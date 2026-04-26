"""
Smarter AIA file download: click folders to expand, then download individual files inside.
Priority: '3rd Party Inspections' folder (2.8 MB — has BCC's exact scope), then sample
drawings for MEP/FP/structural from '100% Drawings and Specs'.
"""
import asyncio, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Turner Construction Company\AIA Headquarters Renovation\drawings")
OUT.mkdir(parents=True, exist_ok=True)

FILE_EXT_RE = re.compile(r"\.(pdf|dwg|xlsx|xls|docx|doc|zip|rvt|ifc)$", re.I)


async def _list_file_rows(page):
    """Return list of (name, size) visible in the current Files view."""
    return await page.evaluate(
        """
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'))
              .filter(r => !r.classList.contains('ReactVirtualized__Table__headerRow'));
            return rows.map(r => ({
                text: (r.innerText||'').trim(),
                cellsCount: r.querySelectorAll('[role="gridcell"]').length
            }));
        }
        """
    )


async def _click_by_text(page, text):
    """Click the most specific element containing the given text."""
    try:
        loc = page.locator(f"[role='row']:has-text('{text}')").first
        if await loc.count() == 0:
            loc = page.get_by_text(text, exact=False).first
        if await loc.count() == 0:
            return False
        await loc.scroll_into_view_if_needed()
        await loc.click(timeout=10000)
        return True
    except Exception as e:
        print(f"    [click_err {text}] {e}")
        return False


async def _try_download_click(page, locator, dst_dir: Path):
    try:
        async with page.expect_download(timeout=60000) as dl_info:
            await locator.click()
        dl = await dl_info.value
        fname = re.sub(r'[\\/:*?"<>|]', '_', dl.suggested_filename or "download.bin")
        target = dst_dir / fname
        await dl.save_as(str(target))
        print(f"    [saved] {target.name} ({target.stat().st_size // 1024} KB)")
        return True
    except Exception as e:
        print(f"    [no-download] {e}")
        return False


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.goto("https://app.buildingconnected.com/opportunities/65985942673770b0374dba83/files",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        print(f"URL: {page.url}")
        rows_before = await _list_file_rows(page)
        print(f"[init] {len(rows_before)} rows in Files tab")
        for r in rows_before[:15]:
            print(f"  → {r['text'][:100]}")

        # Step 1: click '3rd Party Inspections' folder to expand
        print(f"\n[step 1] click '3rd Party Inspections' folder")
        clicked = await _click_by_text(page, "3rd Party Inspections")
        if not clicked:
            print("  could not click")
        else:
            await page.wait_for_timeout(3000)
            print(f"  URL after: {page.url}")
            rows_after = await _list_file_rows(page)
            print(f"  {len(rows_after)} rows after click (delta {len(rows_after) - len(rows_before)})")
            # New rows
            before_texts = {r["text"] for r in rows_before}
            new_rows = [r for r in rows_after if r["text"] not in before_texts]
            print(f"  {len(new_rows)} new rows appeared:")
            for nr in new_rows[:30]:
                print(f"    • {nr['text'][:120]}")

            # For each new row that looks like a file (has extension), click to download
            for nr in new_rows:
                t = nr["text"]
                # Try to find a file-extension marker in the text
                if FILE_EXT_RE.search(t.split("\n")[0]):
                    name_line = t.split("\n")[0]
                    print(f"\n  [file] {name_line}")
                    try:
                        loc = page.locator(f"[role='row']:has-text('{name_line[:40]}')").first
                        if await loc.count() > 0:
                            await _try_download_click(page, loc, OUT)
                    except Exception as e:
                        print(f"    [err] {e}")

        await browser.close()


asyncio.run(run())
