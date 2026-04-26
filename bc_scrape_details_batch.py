"""
批量抓取 BC bid board 中 "未起草 + 未过期 + in-scope" 项目的详情。

输入:  bc_bidboard_projects.json （由 bc_collect_bidboard_cdp.py 生成）
输出:  bc_project_details.json   （每个项目的完整详情）

详情页字段（从 Overview 文本解析）:
  - project_name
  - trade_names (package)
  - location     ← 完整街道地址
  - project_size
  - project_info (description)
  - trade_instructions
  - client_company
  - contact_name
  - contact_phone
  - contact_email
  - date_due
  - rfis_due
  - invited_via
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"
BASE_DIR = Path(__file__).resolve().parent
IN_FILE = BASE_DIR / "bc_bidboard_projects.json"
OUT_FILE = BASE_DIR / "bc_project_details.json"
PENDING_DIR = BASE_DIR / "Pending_Approval" / "Outbound"

# 通过 NW/NE/SE/SW 或城市名判断 DC-area
DC_STRONG = re.compile(r"\b(NW|NE|SE|SW)\b", re.I)
DC_WEAK = re.compile(r"\b(washington, ?dc|district of columbia)\b", re.I)
IN_SCOPE_STATES = re.compile(r"\b(DC|Maryland|MD|Virginia|VA)\b")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _parse_due(d: str) -> datetime:
    if not d:
        return datetime(9999, 1, 1)
    try:
        return datetime.strptime(d.split()[0], "%m/%d/%Y")
    except Exception:
        return datetime(9999, 1, 1)


def _pending_slugs() -> set[str]:
    out = set()
    if not PENDING_DIR.exists():
        return out
    for f in PENDING_DIR.iterdir():
        nm = f.name
        if nm.startswith("Proposal_Draft_"):
            core = nm[len("Proposal_Draft_"):].rsplit(".md", 1)[0]
        elif nm.startswith("BC_Proposal_") and nm.endswith("_Draft.md"):
            core = nm[len("BC_Proposal_"):-len("_Draft.md")]
        else:
            continue
        out.add(_norm(core.replace("_", " ")))
    return out


# 详情页文本里已知 label 列表（按出现顺序），value = 下一非空行；多行 value 取到下一个 label 前
# 注意 "Project Information" / "Trade Specific Instructions" / description 会多行
LABELS = [
    "Request Type", "Number", "Project Name", "Trade Name(s)",
    "Location", "Project Size", "Project Information",
    "Trade Specific Instructions",
    "Date Due", "Job Walk", "RFIs Due", "Expected Start", "Expected Finish", "Date Invited",
    "Architect", "Engineer", "Property Owner", "Property Tenant",
    "Owning Office", "Market Sector", "Priority", "ROM",
    "Additional info", "Tags",
]
LABEL_SET = set(LABELS)
SEPARATORS = {"--", "-"}


def parse_detail_body(body: str) -> dict:
    lines = [ln.strip() for ln in body.splitlines()]
    # compress multi-blank
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line in LABEL_SET:
            # collect value lines until next label, empty-heavy stretch, or known stop
            vals = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in LABEL_SET:
                    break
                # 停在另一个已知节标题
                if nxt in {"Related organizations", "Team Summary", "Activity",
                           "Internal Use", "Estimating", "Resourcing", "Revenue",
                           "Project dates", "General info", "Project Details",
                           "Client", "Overview", "Files", "Messages", "Bid Form",
                           "Opportunity Summary", "Project Information"}:
                    # 但 "Project Information" 就是我们想要的 key 本身 — 用下标兜住
                    if nxt == "Project Information" and line != "Project Information":
                        break
                    if nxt != "Project Information":
                        break
                if nxt:
                    vals.append(nxt)
                j += 1
                # 防 runaway: 多行 description 以空行/下一 label 终止
                if len(vals) > 30:
                    break
            # Project Information 可能是多行 paragraph — 合并
            val = " ".join(vals).strip() if line in ("Project Information", "Trade Specific Instructions") else (vals[0] if vals else "")
            if val and val not in SEPARATORS:
                out[line] = val
            i = j
            continue
        i += 1

    # Client block 单独 parse: 定位 "Client" 行
    try:
        idx = next(k for k, ln in enumerate(lines) if ln == "Client")
        block = []
        for k in range(idx + 1, min(idx + 15, len(lines))):
            ln = lines[k]
            if ln in ("Project Details", "Overview", "Files", "Messages", "Bid Form", "Team Summary"):
                break
            block.append(ln)
        # 典型：
        # Bidding to multiple clients? Add opportunity »
        # <CLIENT COMPANY>
        # <CONTACT NAME>
        # " | "
        # <PHONE>
        # " | "
        # <EMAIL>
        non_sep = [b for b in block if b and b != "|" and "Bidding to multiple" not in b and "Add opportunity" not in b]
        if non_sep:
            out["client_company"] = non_sep[0]
            if len(non_sep) > 1:
                out["contact_name"] = non_sep[1]
            for b in non_sep:
                if "@" in b and "." in b:
                    out["contact_email"] = b.strip()
                if re.search(r"\+?\d[\d\s\-\(\)\.x]{6,}", b) and "@" not in b:
                    out["contact_phone"] = b.strip()
    except StopIteration:
        pass

    return out


async def scrape_one(page, detail_url: str, timeout_ms: int = 25000) -> dict:
    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as e:
        return {"_error": f"goto failed: {e}", "detail_url": detail_url}
    # 等 Overview 文本就绪
    try:
        await page.wait_for_selector("text=Location", timeout=8000)
    except Exception:
        pass
    await page.wait_for_timeout(1200)
    body = await page.inner_text("body")
    parsed = parse_detail_body(body)
    parsed["detail_url"] = detail_url
    parsed["_body_chars"] = len(body)
    return parsed


async def run():
    projs = json.loads(IN_FILE.read_text(encoding="utf-8"))
    pending = _pending_slugs()
    today = datetime(2026, 4, 17)

    # 筛：in-scope + 未起草 + 未过期
    todo = []
    for p in projs:
        if not p.get("in_scope"):
            continue
        if _norm(p["project"]) in pending:
            continue
        due = _parse_due(p["due_dates"][0] if p["due_dates"] else "")
        if due < today:
            continue
        if not p.get("detail_url"):
            continue
        todo.append(p)

    print(f"待抓取 {len(todo)} 个项目详情")
    for p in todo:
        due = p["due_dates"][0] if p["due_dates"] else "—"
        print(f"  [{'/'.join(p['tabs'])}] due {due:<25} {p['project'][:55]}")

    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "buildingconnected" in (pg.url or "")), None) or ctx.pages[0]

        results = []
        for i, p in enumerate(todo, 1):
            print(f"\n[{i}/{len(todo)}] {p['project'][:60]}")
            d = await scrape_one(page, p["detail_url"])
            d["_bidboard"] = {
                "project": p["project"],
                "tabs": p["tabs"],
                "due_dates": p["due_dates"],
                "client_listed": p["client"],
                "contact_listed": p["contact"],
                "location_listed": p["location"],
                "opportunity_id": p["opportunity_id"],
            }
            # 用详情页 Location 重判 DC
            addr = d.get("Location", "") or ""
            if DC_STRONG.search(addr) or DC_WEAK.search(addr) or IN_SCOPE_STATES.search(addr):
                d["_dc_confirmed"] = True
            else:
                d["_dc_confirmed"] = False
            results.append(d)
            loc = d.get("Location", "")
            em = d.get("contact_email", "")
            confirm = "DC ✓" if d["_dc_confirmed"] else "⚠️ out-of-scope?"
            print(f"  → {confirm} | {loc[:80]}")
            if em:
                print(f"  email: {em}")

        OUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[OUT] {len(results)} 项目详情 → {OUT_FILE.name}")

        # 统计
        dc_ok = [r for r in results if r.get("_dc_confirmed")]
        dc_out = [r for r in results if not r.get("_dc_confirmed")]
        print(f"\n确认 DC/MD/VA: {len(dc_ok)} | 疑似范围外: {len(dc_out)}")
        for r in dc_out:
            print(f"  [OUT?] {r.get('Project Name', '?')} — {r.get('Location', '(no location)')}")

        try:
            await browser.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run())
