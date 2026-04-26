"""Inspect what element inside the Name cell is actually clickable for navigation."""
import asyncio, json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])

        if "pipeline" not in (page.url or ""):
            await page.goto("https://app.buildingconnected.com/opportunities/pipeline", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        info = await page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'))
              .filter(r => !r.classList.contains('ReactVirtualized__Table__headerRow'));
            if (!rows.length) return null;
            const r = rows[0];
            const cells = Array.from(r.querySelectorAll('[role="gridcell"]'));
            const nameCell = cells[2];
            // Describe all clickable descendants of name cell
            const descendants = Array.from(nameCell.querySelectorAll('*'));
            const candidates = [];
            for (const el of descendants) {
                const tag = el.tagName;
                const role = el.getAttribute('role');
                const href = el.getAttribute('href');
                const dataId = el.getAttribute('data-id');
                const dataTestId = el.getAttribute('data-testid');
                const clickable = el.onclick !== null || role === 'link' || tag === 'A' || tag === 'BUTTON';
                const txt = (el.innerText || '').trim().slice(0, 50);
                if (clickable || href || dataTestId || (role && role !== 'gridcell')) {
                    candidates.push({tag, role, href, dataId, dataTestId, txt, class: (el.className||'').slice(0,80)});
                }
            }
            return {
                nameCellHTML: nameCell.outerHTML.slice(0, 2000),
                candidates: candidates.slice(0, 20)
            };
        }
        """)
        print(json.dumps(info, indent=2, ensure_ascii=False))
        await browser.close()

asyncio.run(run())
