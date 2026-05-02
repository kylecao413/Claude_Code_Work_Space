"""
Standalone bidboard scraper — uses saved .buildingconnected_cookies.json.
Doesn't require Chrome with remote-debugging port.

Output: bc_bidboard_latest.json (overwrites existing).
"""
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).resolve().parent
COOKIES = BASE / ".buildingconnected_cookies.json"
OUT = BASE / "bc_bidboard_latest.json"
PIPELINE_URL = "https://app.buildingconnected.com/"
BIDBOARD_PATHS = ["/bid-board", "/bidboard", "/pipeline", "/opportunities"]


async def _scroll_and_collect(page, tab_name: str) -> list[dict]:
    """Scroll the bidboard table and capture every visible opportunity row."""
    await page.wait_for_timeout(2500)
    seen: dict[str, dict] = {}
    last_count = -1
    stagnant = 0
    for _ in range(80):
        rows = await page.evaluate(
            r"""
            () => {
              const out = [];
              const seen = new Set();
              const links = document.querySelectorAll('a[href*="/opportunities/"]');
              for (const a of links) {
                const m = a.href.match(/opportunities\/([a-f0-9]{24})/);
                if (!m) continue;
                const oppId = m[1];
                if (seen.has(oppId)) continue;
                seen.add(oppId);
                let row = a.closest('[role="row"], tr, [class*="row"]');
                if (!row) continue;
                const txt = row.innerText || "";
                out.push({opp_id: oppId, opp_href: a.href, text: txt.slice(0, 600)});
              }
              return out;
            }
            """
        )
        for r in rows:
            seen.setdefault(r["opp_id"], r)
        if len(seen) == last_count:
            stagnant += 1
            if stagnant >= 4:
                break
        else:
            stagnant = 0
        last_count = len(seen)
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(900)
    out = []
    for r in seen.values():
        r["tab"] = tab_name
        out.append(r)
    return out


async def _click_tab(page, label: str) -> bool:
    selectors = [
        f"div.styled__StyledFilterText-sc-1pa8xbg-8:text('{label}')",
        f"[data-testid*='filter']:has-text('{label}')",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.click(timeout=5000)
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            pass
    try:
        btn = page.get_by_text(label, exact=True).first
        await btn.click(timeout=5000)
        await page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"  [WARN] tab '{label}' click failed: {e}")
        return False


async def _ensure_unfiltered(page):
    try:
        banner = page.locator("text=/Viewing\\s+\\d+\\s+of your office/")
        if await banner.count() > 0:
            link = page.get_by_text("View them all", exact=False).first
            if await link.count() > 0:
                await link.click()
                await page.wait_for_timeout(3000)
                print("  [OK] unfiltered to all-office")
    except Exception:
        pass


async def main():
    if not COOKIES.exists():
        print(f"[ERR] no cookie file at {COOKIES}")
        return 1
    cookies = json.loads(COOKIES.read_text(encoding="utf-8"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto(PIPELINE_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2000)
        # Click "Bid Board" link in sidebar
        try:
            await page.get_by_text("Bid Board", exact=True).first.click(timeout=5000)
            await page.wait_for_timeout(3500)
            print(f"[INFO] After Bid Board click: {page.url}")
        except Exception as e:
            print(f"[WARN] Bid Board click failed ({e}); trying URL fallbacks")
            for pth in BIDBOARD_PATHS:
                try:
                    await page.goto(f"https://app.buildingconnected.com{pth}", wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2500)
                    body_check = await page.evaluate("document.body.innerText")
                    if "could not be found" not in body_check[:500]:
                        print(f"[INFO] Found bidboard at: {page.url}")
                        break
                except Exception:
                    continue
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        body = await page.evaluate("document.body.innerText")
        Path(BASE / "bc_pipeline_body_debug.txt").write_text(body, encoding="utf-8")
        print(f"[DEBUG] body len={len(body)} → bc_pipeline_body_debug.txt; URL={page.url}")

        if "login" in page.url.lower() or "auth" in page.url.lower():
            print("[ERR] cookies expired — page redirected to login")
            await browser.close()
            return 2

        all_rows: list[dict] = []
        tab_bodies: dict[str, str] = {}
        for tab in ["Undecided", "Accepted"]:
            print(f"=== Tab: {tab} ===")
            if not await _click_tab(page, tab):
                continue
            await _ensure_unfiltered(page)
            items = await _scroll_and_collect(page, tab)
            print(f"  [{tab}] {len(items)} rows")
            all_rows.extend(items)
            # capture full body innerText for this tab to recover date/location
            body = await page.evaluate("document.body.innerText")
            tab_bodies[tab] = body
            Path(BASE / f"bc_bidboard_{tab.lower()}_body.txt").write_text(body, encoding="utf-8")

        # dedup keeping first-seen tab
        dedup: dict[str, dict] = {}
        for r in all_rows:
            dedup.setdefault(r["opp_id"], r)
        rows = list(dedup.values())
        OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[OUT] {len(rows)} unique opportunities → {OUT.name}")

        await browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
