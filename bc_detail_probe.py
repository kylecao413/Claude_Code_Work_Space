"""
Probe: 点击 Bid Board 一行 → 跳转详情页 → 抓关键字段 → 回退。
"""
import asyncio, sys
from playwright.async_api import async_playwright
from pathlib import Path

CDP_URL = "http://127.0.0.1:9222"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])

        print(f"[probe] current: {page.url}")
        # Force fresh pipeline load
        await page.goto("https://app.buildingconnected.com/opportunities/pipeline", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Click Undecided tab
        for label in ["Undecided"]:
            try:
                loc = page.locator(f"div.styled__StyledFilterText-sc-1pa8xbg-8:text('{label}')").first
                if await loc.count() > 0:
                    await loc.click()
                    await page.wait_for_timeout(2000)
                    print(f"[probe] clicked tab {label}")
            except Exception as e:
                print(f"[probe] tab click err: {e}")
        # View them all
        try:
            loc = page.get_by_text("View them all", exact=False).first
            if await loc.count() > 0:
                await loc.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        # Get first data row text, click the Name cell (index 2 of gridcells)
        info = await page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'))
              .filter(r => !r.classList.contains('ReactVirtualized__Table__headerRow'));
            if (rows.length === 0) return null;
            const first = rows[0];
            const cells = Array.from(first.querySelectorAll('[role="gridcell"]'));
            // Name cell is typically index 2 (after assign and ??)
            // Find cell whose text looks like a project name (the longest of first 4)
            const candidates = cells.slice(0, 6).map((c, i) => ({i, text: (c.innerText||'').trim()}));
            return {row_text: first.innerText.trim().slice(0, 300), cells_sample: candidates};
        }
        """)
        print(f"[probe] first row info: {info}")

        # Click the row itself (BC usually makes the whole row clickable)
        row_loc = page.locator("[role='row']").nth(1)  # index 0 is header
        if await row_loc.count() > 0:
            print("[probe] clicking first data row...")
            # click on the name cell specifically
            name_cell = row_loc.locator("[role='gridcell']").nth(2)
            if await name_cell.count() > 0:
                await name_cell.click()
            else:
                await row_loc.click()
            await page.wait_for_timeout(4000)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            print(f"[probe] after click URL = {page.url}")

            Path("bc_pipeline_dump").mkdir(exist_ok=True)
            Path("bc_pipeline_dump/detail_sample.html").write_text(await page.content(), encoding="utf-8")
            body = await page.inner_text("body")
            Path("bc_pipeline_dump/detail_sample.txt").write_text(body, encoding="utf-8")
            print(f"[probe] saved detail page dumps ({len(body)} chars)")
            # Quick peek
            print("---- first 1500 chars of detail body ----")
            print(body[:1500])
        else:
            print("[probe] no rows found")

        await browser.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
