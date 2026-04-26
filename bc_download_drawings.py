"""
Download large (MB-class) files from a BC project detail page's Files tab
into ../Projects/[Client]/[Project]/drawings/.

Usage:
    python bc_download_drawings.py <opportunity_id_or_url> <client> <project>

Skips KB-sized files (ITB/SOW/forms) per Kyle 2026-04-22 rule.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"
PROJECTS_ROOT = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")


def _is_drawing(filename: str, size_str: str) -> bool:
    """True if the file is MB-sized AND name looks like drawings/permit set."""
    s = size_str.lower()
    if not s:
        return False
    if "mb" in s or "gb" in s:
        # parse MB value
        m = re.search(r"([\d.]+)\s*(mb|gb)", s)
        if not m:
            return False
        v = float(m.group(1))
        if m.group(2) == "gb":
            v *= 1024
        # Require >= 1 MB (skip tiny MB files like amendments)
        return v >= 1.0
    return False


def _sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


async def download_from_files_tab(opp_id_or_url: str, client: str, project: str) -> list[Path]:
    if opp_id_or_url.startswith("http"):
        base = opp_id_or_url.split("?")[0].split("/files")[0].split("/info")[0]
        files_url = base + "/files"
    else:
        files_url = f"https://app.buildingconnected.com/opportunities/{opp_id_or_url}/files"

    out_dir = PROJECTS_ROOT / _sanitize(client) / _sanitize(project) / "drawings"
    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        await page.goto(files_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Parse rows: each file is a row with Name / Size / Date
        file_rows = await page.evaluate(
            """
            () => {
                // File rows are table rows inside the Files tab
                const rows = Array.from(document.querySelectorAll('[role="row"]'))
                    .filter(r => !r.classList.contains('ReactVirtualized__Table__headerRow'));
                return rows.map(r => {
                    const cells = Array.from(r.querySelectorAll('[role="gridcell"]'));
                    const txt = cells.map(c => (c.innerText || '').trim());
                    return { cells: txt, outerHTML: r.outerHTML.slice(0, 500) };
                });
            }
            """
        )
        # Heuristic: cells usually [name, indicator, size, date]
        targets = []
        for r in file_rows:
            cells = r.get("cells", [])
            if len(cells) < 3:
                continue
            name = cells[0]
            # size can be in cells[2] or later
            size = ""
            for c in cells[1:]:
                if re.search(r"\b(kb|mb|gb)\b", c.lower()):
                    size = c
                    break
            if _is_drawing(name, size):
                targets.append((name, size))

        print(f"[info] {len(file_rows)} files on page; {len(targets)} look like drawings (MB+)")
        for name, size in targets:
            print(f"  → {name}  ({size})")

        saved = []
        for name, size in targets:
            # Click the row by name to trigger download
            try:
                locator = page.get_by_text(name, exact=False).first
                if await locator.count() == 0:
                    print(f"  [skip] can't locate element for: {name}")
                    continue
                async with page.expect_download(timeout=120000) as dl_info:
                    await locator.click()
                dl = await dl_info.value
                target = out_dir / _sanitize(dl.suggested_filename or name)
                await dl.save_as(str(target))
                saved.append(target)
                print(f"  [ok] saved → {target.name}  ({target.stat().st_size // 1024} KB)")
            except Exception as e:
                print(f"  [fail] {name}: {e}")

        try:
            await browser.close()
        except Exception:
            pass
    return saved


async def main():
    if len(sys.argv) < 4:
        print("Usage: python bc_download_drawings.py <opp_id_or_url> <client> <project>")
        sys.exit(1)
    opp = sys.argv[1]
    client = sys.argv[2]
    project = sys.argv[3]
    saved = await download_from_files_tab(opp, client, project)
    print(f"\n[done] saved {len(saved)} file(s)")
    for s in saved:
        print(f"  {s}")


if __name__ == "__main__":
    asyncio.run(main())
