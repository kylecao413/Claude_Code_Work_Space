"""Quick one-shot: inspect current BC pipeline page row structure in detail."""
import asyncio, json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.wait_for_timeout(500)

        data = await page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'));
            return rows.slice(0, 10).map((r, i) => ({
                idx: i,
                text: (r.innerText || '').trim().slice(0, 400),
                anchors: Array.from(r.querySelectorAll('a[href]'))
                    .map(a => ({ href: a.getAttribute('href'), text: (a.innerText || '').trim().slice(0, 80) })),
                data_ids: Array.from(r.querySelectorAll('[data-id]'))
                    .slice(0, 5).map(e => e.getAttribute('data-id')),
                clickable: Array.from(r.querySelectorAll('[data-testid*="opportunity" i], [id*="opportunity" i]'))
                    .slice(0, 5).map(e => ({id: e.getAttribute('id'), dtid: e.getAttribute('data-testid')}))
            }));
        }
        """)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        await browser.close()

asyncio.run(run())
