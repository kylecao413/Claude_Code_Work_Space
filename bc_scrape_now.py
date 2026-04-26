"""
Scrape BC Bid Board (Undecided + Accepted tabs) via CDP with updated 2026-04 selectors.
- Tab selector: div[class^="smallFilters"] filtered by text
- Row: .ReactVirtualized__Table__row
- Outputs: bc_bidboard_latest.json, bc_bidboard_new_projects.md
"""
from __future__ import annotations
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

CDP = "http://127.0.0.1:9222"
BASE = Path(__file__).resolve().parent
OUT_JSON = BASE / "bc_bidboard_latest.json"
OUT_NEW = BASE / "bc_bidboard_new_projects.md"
PENDING_DIR = BASE / "Pending_Approval" / "Outbound"

DC_KEYS = ["washington", "district of columbia", " dc", ", dc", " nw", " ne", " se", " sw"]


async def click_tab(page, label: str) -> bool:
    loc = page.locator('div[class^="smallFilters"]').filter(has_text=label).first
    if await loc.count() > 0:
        await loc.click()
        await page.wait_for_timeout(2500)
        return True
    return False


async def ensure_unfiltered(page) -> bool:
    try:
        banner = page.locator("text=/Viewing\\s+\\d+\\s+of your office/")
        if await banner.count() > 0:
            link = page.get_by_text("View them all", exact=False).first
            if await link.count() > 0:
                await link.click()
                await page.wait_for_timeout(2500)
                return True
    except Exception:
        pass
    return False


SCROLL_BATCH_JS = """
() => {
    const out = [];
    document.querySelectorAll('.ReactVirtualized__Table__row').forEach(r => {
        const cells = Array.from(r.querySelectorAll('.ReactVirtualized__Table__rowColumn'));
        const a = r.querySelector('a[href*="/opportunities/"]');
        let opp_id = ''; let opp_href = '';
        if (a) {
            opp_href = a.href;
            const m = opp_href.match(/\\/opportunities\\/([^\\/?#]+)/);
            if (m) opp_id = m[1];
        }
        const cellText = cells.map(c => (c.innerText || '').trim());
        out.push({opp_id, opp_href, cells: cellText});
    });
    return out;
}
"""

SCROLL_STEP_JS = """
() => {
    const g = document.querySelector('.ReactVirtualized__Grid') || document.querySelector('.ReactVirtualized__Table__Grid');
    if (!g) return {ok: false};
    const before = g.scrollTop;
    g.scrollTop = g.scrollTop + 800;
    return {before, after: g.scrollTop, max: g.scrollHeight};
}
"""


async def scroll_collect(page, tab_name: str):
    rows_by_key = {}
    stable = 0
    for i in range(120):
        batch = await page.evaluate(SCROLL_BATCH_JS)
        for row in batch:
            k = row['opp_id'] or '|'.join(row['cells'])
            rows_by_key[k] = row
        info = await page.evaluate(SCROLL_STEP_JS)
        await page.wait_for_timeout(550)
        if info.get('after', 0) == info.get('before', 0):
            stable += 1
        else:
            stable = 0
        if stable >= 3:
            break
    print(f"  [{tab_name}] collected {len(rows_by_key)} rows")
    return list(rows_by_key.values())


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def pending_slugs() -> set:
    out = set()
    if not PENDING_DIR.exists():
        return out
    for f in PENDING_DIR.iterdir():
        nm = f.name
        if nm.startswith("Proposal_Draft_"):
            core = nm[len("Proposal_Draft_"):].rsplit(".md", 1)[0]
        elif nm.startswith("BC_Proposal_") and nm.endswith("_Draft.md"):
            core = nm[len("BC_Proposal_"):-len("_Draft.md")]
        elif nm.startswith("Email_"):
            core = nm[len("Email_"):].rsplit("_2026", 1)[0]
        else:
            continue
        out.add(norm(core))
    return out


async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = None
        for pg in ctx.pages:
            if "buildingconnected" in (pg.url or "").lower():
                page = pg
                break
        if page is None:
            page = ctx.pages[0]
        await page.goto("https://app.buildingconnected.com/opportunities/pipeline", wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)
        await ensure_unfiltered(page)
        await page.wait_for_timeout(1500)

        all_rows = []
        for tab in ["Undecided", "Accepted"]:
            clicked = await click_tab(page, tab)
            if not clicked:
                print(f"  [SKIP] no tab {tab}")
                continue
            await page.wait_for_timeout(1500)
            await ensure_unfiltered(page)
            await page.wait_for_timeout(1500)
            rows = await scroll_collect(page, tab)
            for r in rows:
                r['tab'] = tab
            all_rows.extend(rows)

        uniq = {}
        for r in all_rows:
            k = f"{r.get('opp_id','')}|{r.get('tab','')}"
            uniq[k] = r
        print(f"TOTAL UNIQ: {len(uniq)}")

        OUT_JSON.write_text(json.dumps(list(uniq.values()), indent=2, ensure_ascii=False))

        by_opp = {}
        for r in uniq.values():
            oid = r.get('opp_id', '')
            if not oid:
                continue
            if oid not in by_opp:
                by_opp[oid] = {
                    'opp_id': oid,
                    'cells_sample': r.get('cells', []),
                    'tabs': set(),
                    'href': r.get('opp_href', ''),
                }
            by_opp[oid]['tabs'].add(r.get('tab', ''))

        pending = pending_slugs()
        new_items = []
        for oid, rec in by_opp.items():
            txt = ' '.join(rec['cells_sample']).lower()
            first = rec['cells_sample'][1] if len(rec['cells_sample']) > 1 else ''
            parts = first.split('\n')
            proj = parts[0] if parts else ''
            pkg = parts[1] if len(parts) > 1 else ''
            in_scope = any(k in txt for k in DC_KEYS) or 'Accepted' in rec['tabs']
            slug_norm = norm(proj)
            matched = any(slug_norm and (slug_norm in ps or ps in slug_norm) for ps in pending)
            rec['in_scope'] = in_scope
            rec['has_draft'] = matched
            rec['proj'] = proj
            rec['pkg'] = pkg
            if in_scope and not matched:
                new_items.append(rec)

        lines = [
            "# BC Bid Board — New DC-area Projects\n",
            f"Scraped {len(by_opp)} unique opportunities.",
            f"New (DC-area + no existing draft): **{len(new_items)}**",
            "",
            "---",
            "",
        ]
        for it in new_items:
            tabs_s = "/".join(sorted(it['tabs']))
            lines.append(f"## {it['proj']}")
            lines.append(f"- **Bid Package**: {it['pkg']}")
            lines.append(f"- **Tabs**: {tabs_s}")
            lines.append(f"- **URL**: {it['href']}")
            lines.append(f"- **Row dump**: {' | '.join(it['cells_sample'])[:500]}")
            lines.append("")
        OUT_NEW.write_text('\n'.join(lines), encoding='utf-8')
        print(f"[OK] {len(new_items)} new DC-area projects -> {OUT_NEW}")


asyncio.run(main())
