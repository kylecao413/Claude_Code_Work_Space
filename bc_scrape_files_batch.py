"""
对 6 个之前被删的项目，进 BC Files tab 抓文件列表。
基于文件名推断 scope：
  - SOW / Scope of Work
  - Drawings / Specs
  - 图纸数量（能看出 # of sheets / MB 大小估计）
  - Fire alarm / Sprinkler / Plumbing / Foundation / MEP 关键词
"""
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"

PROJECTS = [
    ("US GPO - QCIM Room Renovation (Encon)",            "https://app.buildingconnected.com/opportunities/69b95d3c4c38a8bbb7b532eb/info"),
    ("Repair Faulty Circuit Breaker B94 at JBAB (Desbuild)", "https://app.buildingconnected.com/opportunities/69caaa2aa70603288203c747/info"),
    ("GPO-NARA 040ADV-26-R-0016 (CJW)",                  "https://app.buildingconnected.com/opportunities/69c2fa0e874a4c1761196d0b/info"),
    ("USAF Repair Faulty Circuit Breaker B94 (CJW)",     "https://app.buildingconnected.com/opportunities/69c42f1e2343aa106845376f/info"),
    ("(PreVeil) P001U Hazardous Waste Storage (CJW)",    "https://app.buildingconnected.com/opportunities/69d7fbd2dd21497aa1965251/info"),
    ("USAF Demolition Blanchard Hall B1302 (CJW)",       "https://app.buildingconnected.com/opportunities/69dff8f14f7b3329abd72f77/info"),
]


def classify_files(filenames: list[str]) -> dict:
    """Keyword heuristics on file names."""
    text = "\n".join(filenames).lower()
    flags = {
        "has_sow":          any(k in text for k in ["sow", "scope of work", "statement of work"]),
        "has_drawings":     any(k in text for k in [".dwg", "drawings", "plans", "set", "perm"]),
        "has_specs":        "spec" in text,
        "has_foundation":   "foundation" in text or "footing" in text,
        "has_plumbing":     any(k in text for k in ["plumb", "underground", "groundwork", "ug plb"]),
        "has_sprinkler":    any(k in text for k in ["sprinkler", "fire suppression", "fp drawing"]),
        "has_fire_alarm":   any(k in text for k in ["fire alarm", "fa drawing"]),
        "has_insulation":   "insulation" in text,
        "has_framing":      any(k in text for k in ["framing", "struct"]),
        "has_mep":          any(k in text for k in ["mechanical", "electrical", "mep", "hvac"]),
        "has_environmental":"environmental" in text or "annex" in text,
        "has_wage_det":     "wage" in text,
        "has_amendment":    "amendment" in text,
    }
    # Judge scale
    mb_sum = 0
    for fn in filenames:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(kb|mb|gb)", fn.lower())
        if m:
            v = float(m.group(1))
            unit = m.group(2)
            mb = v / 1000 if unit == "kb" else (v if unit == "mb" else v * 1000)
            mb_sum += mb
    flags["total_mb"] = round(mb_sum, 1)
    flags["file_count"] = len(filenames)
    return flags


async def scrape_one(page, label: str, info_url: str) -> dict:
    files_url = info_url.replace("/info", "/files")
    try:
        await page.goto(files_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        return {"label": label, "_error": f"goto: {e}"}
    await page.wait_for_timeout(2500)

    # Extract file rows via innerText parsing (Files tab typically lists Name/Size/Date)
    body = await page.inner_text("body")
    # File rows appear after "Name\nIndicator\nSize\nDate Modified\n"
    m = re.search(r"Date Modified\s*\n(.*?)(?:\nAdd new bid invite|\nBuildingConnected|\Z)", body, re.DOTALL)
    file_block = m.group(1).strip() if m else ""

    # Parse: each file has a name, optional indicator, size (KB/MB/GB), date
    # Lines typically: filename / (optional indicator) / "123 KB" / "4/9/2026 at 10:11 AM EDT"
    files = []
    lines = [ln.strip() for ln in file_block.splitlines() if ln.strip()]
    cur = []
    for ln in lines:
        cur.append(ln)
        # Trigger: a line matching date pattern completes a file record
        if re.match(r"\d{1,2}/\d{1,2}/\d{4}", ln):
            # Walk back to find name + size
            size_line = cur[-2] if len(cur) >= 2 else ""
            name_lines = cur[:-2] if len(cur) >= 2 else cur[:-1]
            name = name_lines[0] if name_lines else ""
            files.append({"name": name, "size": size_line, "date": ln})
            cur = []

    filenames = [f"{f['name']}  ({f['size']})" for f in files]
    flags = classify_files(filenames)
    return {
        "label": label,
        "files_url": files_url,
        "file_count": len(files),
        "files": files,
        "flags": flags,
    }


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), ctx.pages[0])
        results = []
        for label, url in PROJECTS:
            print(f"\n=== {label} ===")
            r = await scrape_one(page, label, url)
            results.append(r)
            print(f"  files: {r.get('file_count', 0)}")
            for f in r.get("files", [])[:12]:
                print(f"    • {f['name']}  ({f.get('size','')})")
            flags = r.get("flags", {})
            active = {k: v for k, v in flags.items() if v is True}
            print(f"  flags: {active}")
            print(f"  total size: {flags.get('total_mb', 0)} MB")
        Path("bc_files_scan.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[OUT] bc_files_scan.json")
        await browser.close()

asyncio.run(run())
