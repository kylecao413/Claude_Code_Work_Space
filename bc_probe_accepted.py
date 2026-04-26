"""Debug: Accepted tab 为什么只抓到 1 行。"""
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        if "pipeline" not in (page.url or ""):
            await page.goto("https://app.buildingconnected.com/opportunities/pipeline", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Click Accepted
        await page.locator("div.styled__StyledFilterText-sc-1pa8xbg-8:text('Accepted')").first.click()
        await page.wait_for_timeout(3000)

        # Look for "View them all" explicitly + the filter bar text
        for txt in ["View them all", "View all", "Viewing", "of your office's", "following", "Filtered by"]:
            loc = page.get_by_text(txt, exact=False)
            cnt = await loc.count()
            if cnt:
                for i in range(min(cnt, 3)):
                    try:
                        t = (await loc.nth(i).text_content() or "").strip()[:150]
                        print(f"  '{txt}' [{i}]: {t!r}")
                    except Exception:
                        pass

        row_cnt = await page.locator("[role='row']").count()
        print(f"[rows] {row_cnt}")

        # Dump current visible body first 2000 chars
        body = await page.inner_text("body")
        print("---- body (first 2000) ----")
        print(body[:2000])
        await browser.close()

asyncio.run(run())
