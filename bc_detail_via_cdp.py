"""
Fetch BC project detail pages via CDP (reuses live login session).
Usage: python bc_detail_via_cdp.py <opp_id> [opp_id ...]
Writes: Projects/_bc_detail_<opp_id>.json for each.
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

CDP = "http://127.0.0.1:9222"
BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "_bc_details"
OUT_DIR.mkdir(exist_ok=True)


async def scrape_one(page, opp_id: str) -> dict:
    url = f"https://app.buildingconnected.com/opportunities/{opp_id}/info"
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)
    # Scrape Overview-style fields
    data = await page.evaluate(
        """
        () => {
            const out = { url: location.href, title: '', sections: {} };
            out.title = (document.querySelector('h1, h2')?.innerText || '').trim();
            // Collect labelled pairs
            const labels = document.querySelectorAll('[class*="Label"], [class*="label"], dt, .overviewField__Label, [class*="FieldLabel"]');
            labels.forEach(l => {
                const lab = (l.innerText || '').trim();
                if (!lab || lab.length > 60) return;
                let val = '';
                let sib = l.nextElementSibling;
                if (sib) val = (sib.innerText || '').trim();
                if (!val) {
                    const p = l.parentElement;
                    if (p) {
                        const txt = (p.innerText || '').trim();
                        if (txt.startsWith(lab)) val = txt.slice(lab.length).trim();
                    }
                }
                if (val) out.sections[lab] = val;
            });
            // fallback: grab full page text for manual parse
            out.body_text = (document.body.innerText || '').slice(0, 15000);
            return out;
        }
        """
    )
    return data


async def main():
    ids = sys.argv[1:]
    if not ids:
        print("Usage: python bc_detail_via_cdp.py <opp_id> [opp_id ...]")
        return
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        for oid in ids:
            print(f"\n=== {oid} ===")
            # Open a fresh tab for each opportunity to avoid modal / closed-page issues
            page = await ctx.new_page()
            try:
                data = await scrape_one(page, oid)
                fp = OUT_DIR / f"{oid}.json"
                fp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
                print(f"  title: {data.get('title','')[:120]}")
                print(f"  saved: {fp}")
            except Exception as e:
                print(f"[ERR] {e}")
            finally:
                try:
                    await page.close()
                except Exception:
                    pass


asyncio.run(main())
