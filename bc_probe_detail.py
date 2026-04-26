"""Probe one BC detail page to understand Overview / Location / Contact structure."""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

SAMPLE_URL = "https://app.buildingconnected.com/opportunities/69bd8813672ec8f3a90ae4a3/info"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.goto(SAMPLE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        print(f"[probe] URL: {page.url}")
        body = await page.inner_text("body")
        Path("bc_pipeline_dump/detail_sample.txt").write_text(body, encoding="utf-8")
        Path("bc_pipeline_dump/detail_sample.html").write_text(await page.content(), encoding="utf-8")
        print(f"[probe] body length: {len(body)} chars")

        # Try to find structured label-value near "Location"
        for label in ["Location", "Address", "Project Size", "Sector", "Type", "Description", "Primary Contact", "Bid Instructions", "Scope"]:
            loc = page.get_by_text(label, exact=True)
            cnt = await loc.count()
            if cnt == 0:
                continue
            for i in range(min(cnt, 2)):
                try:
                    parent = await loc.nth(i).evaluate_handle(
                        "el => el.parentElement?.parentElement || el.parentElement"
                    )
                    txt = await (await parent.get_property("innerText")).json_value()
                    print(f"\n[label '{label}' #{i}]:\n  {(txt or '')[:400]}")
                except Exception as e:
                    print(f"  err {label}: {e}")
        await browser.close()

asyncio.run(run())
