"""
AIA download v3: use direct BC download URLs discovered in DOM.
- 扫描 <a href="/_/download/file/...">
- 先收可见的 (已展开的)
- 然后点 "3rd Party Inspections" 展开它
- 再扫一遍
- 用 authenticated page.context.request 拉 bytes
"""
import asyncio, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Turner Construction Company\AIA Headquarters Renovation\drawings")
OUT.mkdir(parents=True, exist_ok=True)


async def _collect_download_links(page):
    """Returns list of (filename, download_url). Pairs anchor with adjacent filename text."""
    return await page.evaluate(
        """
        () => {
            const dlAnchors = Array.from(document.querySelectorAll('a[href*="/_/download/file/"]'));
            const out = [];
            for (const a of dlAnchors) {
                // Find the filename: usually the next sibling or the parent's other child holds the name
                let name = '';
                // try nextElementSibling
                let cur = a.nextElementSibling;
                for (let i = 0; i < 3 && cur; i++) {
                    const t = (cur.textContent || '').trim();
                    if (t && /\\.(pdf|xlsx|xls|docx|doc|zip|dwg|ifc|rvt)$/i.test(t)) { name = t; break; }
                    cur = cur.nextElementSibling;
                }
                // fallback: find any descendant in parent with file extension
                if (!name) {
                    const parent = a.closest('[class*="file"], [class*="row"]') || a.parentElement;
                    if (parent) {
                        const all = Array.from(parent.querySelectorAll('*'));
                        for (const el of all) {
                            const t = (el.textContent || '').trim();
                            if (t && /\\.(pdf|xlsx|xls|docx|doc|zip|dwg|ifc|rvt)$/i.test(t) && t.length < 200) {
                                name = t; break;
                            }
                        }
                    }
                }
                // final fallback: use file_id in URL
                if (!name) {
                    const m = a.getAttribute('href').match(/file\\/([a-f0-9]+)/);
                    name = m ? `bc_file_${m[1]}.bin` : 'unknown.bin';
                }
                out.push({ name, url: a.getAttribute('href') });
            }
            // Dedup by url
            const seen = new Set();
            return out.filter(x => { if (seen.has(x.url)) return false; seen.add(x.url); return true; });
        }
        """
    )


async def _click_folder(page, text):
    try:
        # Target only elements that are exactly the folder name (not the title anchor)
        loc = page.locator(f"div.file-name__FileNameContainer-nh8wiw-0:has-text('{text}'), div[class*='FileNameContainer']:has-text('{text}')").first
        if await loc.count() == 0:
            loc = page.locator(f"div:has-text('{text}'):not(:has(div))").first
        if await loc.count() == 0:
            return False
        await loc.scroll_into_view_if_needed()
        await loc.click(timeout=10000)
        return True
    except Exception as e:
        print(f"  [click err '{text}'] {e}")
        return False


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.goto("https://app.buildingconnected.com/opportunities/65985942673770b0374dba83/files",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # 1) Links visible at initial state
        initial = await _collect_download_links(page)
        print(f"[initial] {len(initial)} downloadable files visible:")
        for x in initial:
            print(f"  • {x['name']}")

        downloaded = []

        async def _download(item):
            url = item["url"]
            if not url.startswith("http"):
                url = "https://app.buildingconnected.com" + url
            try:
                resp = await ctx.request.get(url, timeout=180000)
                if resp.status != 200:
                    print(f"  [http {resp.status}] {item['name']}")
                    return False
                body = await resp.body()
                fname = re.sub(r'[\\/:*?"<>|]', '_', item["name"])
                dst = OUT / fname
                dst.write_bytes(body)
                print(f"  [saved] {dst.name}  ({dst.stat().st_size // 1024} KB)")
                downloaded.append(dst)
                return True
            except Exception as e:
                print(f"  [err] {item['name']}: {e}")
                return False

        # Download initial visible files (except the big folder-like ones that might not be real download URLs)
        print(f"\n[fetch initial] {len(initial)} items")
        for item in initial:
            await _download(item)

        # 2) Click "3rd Party Inspections" to expand
        print("\n[expand '3rd Party Inspections']")
        if await _click_folder(page, "3rd Party Inspections"):
            await page.wait_for_timeout(3500)
            after = await _collect_download_links(page)
            new_items = [x for x in after if x["url"] not in {i["url"] for i in initial}]
            print(f"  {len(new_items)} new files appeared:")
            for x in new_items:
                print(f"    • {x['name']}")
            for item in new_items:
                await _download(item)
        else:
            print("  couldn't click")

        # 3) Also try "Bulletin 1"
        print("\n[expand 'Bulletin 1']")
        if await _click_folder(page, "Bulletin 1"):
            await page.wait_for_timeout(3500)
            after2 = await _collect_download_links(page)
            known = {i["url"] for i in initial}
            new_items = [x for x in after2 if x["url"] not in known]
            print(f"  {len(new_items)} new files (delta from initial):")
            for x in new_items[:20]:
                print(f"    • {x['name']}")
        else:
            print("  couldn't click")

        print(f"\n[total downloaded] {len(downloaded)} files → {OUT}")
        await browser.close()


asyncio.run(run())
