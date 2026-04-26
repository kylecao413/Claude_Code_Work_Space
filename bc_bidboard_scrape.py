"""
bc_bidboard_scrape.py — Navigate BC Bid Board, iterate all tabs,
extract all opportunity names + URLs, match to target projects.

Uses saved cookies from bc_batch_scrape.py login.
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / ".buildingconnected_cookies.json"
OUTPUT_FILE = BASE_DIR / "bc_bidboard_all.json"

TARGET_PROJECTS = [
    "GPO FM Modernization",
    "Washington Endometriosis",
    "800 Connecticut Ave Lobby Renovation",
    "DuFour Center Locker Room Renovation",
    "Union Station Parking Garage Generator Room Upgrade",
    "1300 Girard Street NW",
    "1999 K St Whitebox",
    "GPO - Bldg. B Garage Rood & Skylight Replacement",
    "Ward 8 Senior Center",
    "Garage - Washington, DC",
    "DuFour Center Office Renovation",
    "Office Images DC",
    "Demolition Blanchard Hall Building 1302 - JBAB, DC",
    "1st and M Lobby Renovations",
    "Call Your Mother - DC",
]


def _is_login_page(url: str) -> bool:
    return any(k in url.lower() for k in ("login", "signin", "auth0", "autodesk.com/authenticate"))


async def _load_cookies(context) -> bool:
    if not COOKIES_FILE.exists():
        return False
    try:
        cookies = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
        await context.add_cookies(cookies)
        return True
    except Exception:
        return False


async def _extract_bid_rows(page) -> list[dict]:
    """
    Extract all visible bid board rows from the current tab.
    BC renders rows as divs with clickable areas — we extract
    the text content and any nested opportunity links.
    """
    # Try multiple extraction strategies

    # Strategy 1: Get all opportunity links from the page
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href*="/opportunities/"]'))
            .filter(a => !a.href.includes('/pipeline') && !a.href.includes('/planroom')
                      && !a.href.includes('/calendar') && !a.href.includes('/leaderboard')
                      && !a.href.includes('/analytics') && !a.href.includes('/reports')
                      && !a.href.includes('/settings'))
            .map(a => ({
                href: a.href,
                text: a.innerText.trim().slice(0, 200),
                parent_text: a.closest('tr, [class*="row"], [class*="Row"], div')?.innerText?.trim()?.slice(0, 300) || ''
            }))
    """)

    # Strategy 2: Extract from table rows if present
    rows = await page.evaluate("""
        () => {
            // Look for table-like structures in the bid board
            const allRows = document.querySelectorAll('tr, [role="row"]');
            return Array.from(allRows).map(row => ({
                text: row.innerText.trim().slice(0, 300),
                links: Array.from(row.querySelectorAll('a[href*="/opportunities/"]'))
                    .map(a => ({href: a.href, text: a.innerText.trim()}))
            })).filter(r => r.links.length > 0 || r.text.length > 20);
        }
    """)

    # Strategy 3: Get the full page body and parse for opportunity IDs
    body = await page.inner_text("body")

    # Combine results
    items = []
    seen_hrefs = set()

    for link in links:
        href = link["href"]
        if href not in seen_hrefs:
            seen_hrefs.add(href)
            items.append({
                "name": link["text"],
                "url": href,
                "row_text": link.get("parent_text", ""),
            })

    return items, body


async def _scroll_and_collect(page, tab_name: str) -> list[dict]:
    """Scroll through the bid board tab and collect all items."""
    all_items = []
    body_text = ""

    for scroll_pass in range(10):  # Max 10 scroll passes
        items, body = _items_dummy = await _extract_bid_rows(page)
        body_text = body

        new_count = 0
        seen_urls = {i["url"] for i in all_items}
        for item in items:
            if item["url"] not in seen_urls:
                all_items.append(item)
                seen_urls.add(item["url"])
                new_count += 1

        print(f"  [{tab_name}] Scroll {scroll_pass}: {new_count} new items (total: {len(all_items)})", flush=True)

        if scroll_pass > 0 and new_count == 0:
            break

        # Scroll down
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

    return all_items, body_text


async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        await _load_cookies(context)
        page = await context.new_page()

        # Navigate to BC
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        if _is_login_page(page.url):
            print("NOT LOGGED IN. Run bc_batch_scrape.py first.", file=sys.stderr)
            await browser.close()
            return

        print(f"Logged in. At: {page.url}", flush=True)

        # Navigate to Bid Board
        print("\n[BC] Navigating to Bid Board...", flush=True)
        await page.goto("https://app.buildingconnected.com/opportunities/pipeline", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(4000)
        print(f"[BC] At: {page.url}", flush=True)

        # First, try clicking "View them all" to remove the "following" filter
        try:
            view_all = page.locator("text=View them all")
            if await view_all.count() > 0:
                await view_all.click()
                await page.wait_for_timeout(3000)
                print("[BC] Clicked 'View them all' to remove filter", flush=True)
        except Exception:
            pass

        all_projects = []

        # Tab order: Undecided, Accepted, Submitted
        tabs = ["Undecided", "Accepted", "Submitted"]

        for tab_name in tabs:
            print(f"\n[BC] === Switching to '{tab_name}' tab ===", flush=True)
            try:
                tab_btn = page.locator(f"text={tab_name}").first
                if await tab_btn.count() > 0:
                    await tab_btn.click()
                    await page.wait_for_timeout(4000)
                    print(f"[BC] Clicked '{tab_name}' tab", flush=True)
                else:
                    print(f"[BC] Tab '{tab_name}' not found", flush=True)
                    continue

                # Take screenshot
                await page.screenshot(path=str(BASE_DIR / f"bc_bidboard_{tab_name.lower()}.png"), full_page=True)

                # Scroll and collect all items
                items, body = await _scroll_and_collect(page, tab_name)

                for item in items:
                    item["tab"] = tab_name

                all_projects.extend(items)

                # Also save body text for this tab
                (BASE_DIR / f"bc_bidboard_{tab_name.lower()}_body.txt").write_text(
                    body[:10000], encoding="utf-8"
                )

                print(f"[BC] '{tab_name}' tab: {len(items)} projects found", flush=True)

            except Exception as e:
                print(f"[BC] Error on '{tab_name}' tab: {e}", flush=True)

        # Save all results
        OUTPUT_FILE.write_text(json.dumps(all_projects, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[BC] Total projects across all tabs: {len(all_projects)}", flush=True)
        print(f"[BC] Saved to {OUTPUT_FILE.name}", flush=True)

        # Match against target projects
        print(f"\n[BC] === Matching against {len(TARGET_PROJECTS)} target projects ===", flush=True)

        def normalize(s):
            return re.sub(r'[^a-z0-9\s]', '', s.lower()).strip()

        matches = {}
        for target in TARGET_PROJECTS:
            target_norm = normalize(target)
            target_tokens = set(target_norm.split()) - {"the", "a", "dc", "washington"}
            best_score = 0
            best_match = None

            for proj in all_projects:
                proj_norm = normalize(proj["name"])

                # Exact substring match
                if target_norm in proj_norm or proj_norm in target_norm:
                    score = 1.0
                else:
                    proj_tokens = set(proj_norm.split())
                    if target_tokens:
                        overlap = len(target_tokens & proj_tokens) / len(target_tokens)
                        score = overlap
                    else:
                        score = 0

                if score > best_score:
                    best_score = score
                    best_match = proj

            if best_score >= 0.4 and best_match:
                print(f"  MATCH ({best_score:.0%}): {target}")
                print(f"    → {best_match['name']} [{best_match['tab']}]")
                print(f"    → {best_match['url']}")
                matches[target] = best_match
            else:
                print(f"  NO MATCH: {target} (best: {best_score:.0%})")

        print(f"\n[BC] Matched: {len(matches)}/{len(TARGET_PROJECTS)} projects")

        # Save matches
        match_file = BASE_DIR / "bc_matched_projects.json"
        match_data = {}
        for target, proj in matches.items():
            match_data[target] = {
                "name": proj["name"],
                "url": proj["url"],
                "tab": proj["tab"],
            }
        match_file.write_text(json.dumps(match_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[BC] Matches saved to {match_file.name}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
