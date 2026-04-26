"""Probe BC detail page's Files tab to see structure."""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright

async def run(url):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Click Files tab
        files_tab = page.get_by_role("tab", name="Files")
        if await files_tab.count() == 0:
            files_tab = page.get_by_text("Files", exact=True).first
        if await files_tab.count() > 0:
            await files_tab.click()
            await page.wait_for_timeout(3000)
            print(f"[probe] clicked Files tab. URL now: {page.url}")
        else:
            print("[probe] Files tab not found via role/text")

        Path("bc_pipeline_dump").mkdir(exist_ok=True)
        body = await page.inner_text("body")
        Path("bc_pipeline_dump/files_tab_sample.txt").write_text(body, encoding="utf-8")
        html = await page.content()
        Path("bc_pipeline_dump/files_tab_sample.html").write_text(html, encoding="utf-8")
        print(f"body: {len(body)} chars")
        print("---- first 3000 chars ----")
        print(body[:3000])
        await browser.close()

asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "https://app.buildingconnected.com/opportunities/69caaa2aa70603288203c747/info"))
