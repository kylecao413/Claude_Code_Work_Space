"""Download AIA permit-set files (3rd Party Inspections doc + drawings structure)."""
import asyncio, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Turner Construction Company\AIA Headquarters Renovation\drawings")
OUT.mkdir(parents=True, exist_ok=True)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.goto("https://app.buildingconnected.com/opportunities/65985942673770b0374dba83/files",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Target items (by name). We try to click each and capture a download.
        TARGETS = ["3rd Party Inspections", "100% Drawings and Specs", "Bulletin 1"]
        for name in TARGETS:
            print(f"\n[try] {name}")
            try:
                loc = page.get_by_text(name, exact=False).first
                if await loc.count() == 0:
                    print(f"  [skip] not found")
                    continue
                try:
                    async with page.expect_download(timeout=90000) as dl_info:
                        await loc.click()
                    dl = await dl_info.value
                    fname = dl.suggested_filename or f"{name}.bin"
                    fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
                    dst = OUT / fname
                    await dl.save_as(str(dst))
                    print(f"  [ok] saved → {dst.name}  ({dst.stat().st_size // 1024} KB)")
                except asyncio.TimeoutError:
                    # Not a download — probably expanded a folder. Collect its inner file list.
                    await page.wait_for_timeout(2000)
                    body = await page.inner_text("body")
                    mark = body.find(name)
                    if mark >= 0:
                        slice_after = body[mark: mark + 4000]
                        print(f"  [folder expanded — first 1500 chars of following listing]")
                        print(slice_after[:1500])
                    # Navigate back to top-level files view
                    await page.goto("https://app.buildingconnected.com/opportunities/65985942673770b0374dba83/files",
                                    wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  [err] {e}")

        await browser.close()

asyncio.run(run())
