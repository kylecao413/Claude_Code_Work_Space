"""
通过 CDP 接管已登录的 BC 调试 Chrome，收集 Bid Board 上 Undecided + Accepted
两个 tab 下的全部 bid package。

每行列序（与表头一致，已确认 2026-04-17）：
  cells[0] Assign
  cells[1] (skip, possibly ancillary)
  cells[2] Name  ← 含 <a href="/opportunities/<id>"> + 项目名 + bid package 名
  cells[3] Due Date
  cells[4] Project Size
  cells[5] Location (city + state)
  cells[6] Comments
  cells[7] Client (GC + contact)
  cells[8] Tags
  cells[9] Action

输出：
  bc_bidboard_latest.json          — 所有 package 行（含 opportunity_id/URL）
  bc_bidboard_projects.json        — 按项目名聚合
  bc_bidboard_new_projects.md      — 未出现在 Pending_Approval 的新项目
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"
PIPELINE_URL = "https://app.buildingconnected.com/opportunities/pipeline"
BASE_DIR = Path(__file__).resolve().parent
OUT_ROWS = BASE_DIR / "bc_bidboard_latest.json"
OUT_PROJECTS = BASE_DIR / "bc_bidboard_projects.json"
OUT_NEW_MD = BASE_DIR / "bc_bidboard_new_projects.md"
PENDING_DIR = BASE_DIR / "Pending_Approval" / "Outbound"

# DC-area 关键字：过滤服务范围（Kyle 只做 DC inspection；MD/VA 可以做）
IN_SCOPE_KEYWORDS = [
    "district of columbia", "dc", "washington",
    "maryland", "md", "bethesda", "rockville", "silver spring", "hyattsville",
    "virginia", "va", "arlington", "alexandria", "fairfax", "falls church",
]


async def _get_header_map(page) -> dict[str, int]:
    """返回 {label: cell_index}，从当前可见表头动态建。"""
    hm = await page.evaluate(
        """
        () => {
            const header = document.querySelector('.ReactVirtualized__Table__headerRow');
            if (!header) return {};
            const cols = Array.from(header.querySelectorAll('[role="columnheader"], .ReactVirtualized__Table__headerColumn'));
            const map = {};
            cols.forEach((c, i) => {
                const t = (c.innerText || '').trim();
                if (t) map[t] = i;
            });
            return map;
        }
        """
    )
    return hm or {}


async def _extract_rows(page, header_map: dict[str, int]) -> list[dict]:
    # 提供索引默认（若找不到该列则用 -1）
    idx_name = header_map.get("Name", 2)
    idx_due = header_map.get("Due Date", 3)
    idx_size = header_map.get("Project Size", -1)
    idx_loc = header_map.get("Location", -1)
    idx_client = header_map.get("Client", -1)
    idx_action = header_map.get("Action", -1)

    rows = await page.evaluate(
        f"""
        () => {{
            const rows = Array.from(document.querySelectorAll('[role="row"]'))
              .filter(r => !r.classList.contains('ReactVirtualized__Table__headerRow'));
            return rows.map(r => {{
                const cells = Array.from(r.querySelectorAll('[role="gridcell"]'));
                const get = i => (i >= 0 && cells[i]) ? (cells[i].innerText || '').trim() : '';
                let href = '', opp_id = '';
                // 先尝试 a[href]
                const nameA = r.querySelector('a[href^="/opportunities/"]');
                if (nameA) {{
                    href = nameA.getAttribute('href') || '';
                }} else {{
                    // Accepted tab 用 React Router <Link to="/opportunities/...">
                    const toEl = r.querySelector('[to^="/opportunities/"]');
                    if (toEl) href = toEl.getAttribute('to') || '';
                }}
                const m = href.match(/\\/opportunities\\/([a-f0-9]+)/i);
                if (m) opp_id = m[1];
                return {{
                    href, opportunity_id: opp_id,
                    name_cell: get({idx_name}),
                    due_cell: get({idx_due}),
                    size_cell: get({idx_size}),
                    location_cell: get({idx_loc}),
                    client_cell: get({idx_client}),
                    action_cell: get({idx_action}),
                    raw_text: (r.innerText || '').trim().slice(0, 500)
                }};
            }});
        }}
        """
    )
    out = []
    for r in rows:
        name_lines = [ln.strip() for ln in (r["name_cell"] or "").splitlines() if ln.strip()]
        project = name_lines[0] if name_lines else ""
        package = name_lines[1] if len(name_lines) > 1 else ""
        client_lines = [ln.strip() for ln in (r["client_cell"] or "").splitlines() if ln.strip()]
        client = client_lines[0] if client_lines else ""
        contact = client_lines[1] if len(client_lines) > 1 else ""
        loc_lines = [ln.strip() for ln in (r["location_cell"] or "").splitlines() if ln.strip() and ln.strip() != "–"]
        location = ", ".join(loc_lines)
        due = " ".join((r["due_cell"] or "").splitlines()).strip()
        out.append({
            "project": project,
            "package": package,
            "due_date": due,
            "project_size": r["size_cell"],
            "location": location,
            "client": client,
            "contact": contact,
            "action": r["action_cell"],
            "opportunity_id": r["opportunity_id"],
            "detail_url": f"https://app.buildingconnected.com{r['href']}/info" if r["href"] else "",
        })
    return out


async def _scroll_collect(page, tab_name: str, max_passes: int = 80) -> list[dict]:
    # 每次切 tab 列序会变，重新建 header map
    await page.wait_for_timeout(1500)
    # 等 anchor 渲染 — 每行 Name 单元格应该有 <a href>
    try:
        await page.wait_for_selector("a[href^='/opportunities/']", timeout=8000)
    except Exception:
        pass
    header_map = await _get_header_map(page)
    print(f"  [{tab_name}] header_map: {header_map}")
    dedup: dict[str, dict] = {}
    stuck = 0
    step_px = 400
    last_scroll = -1
    for i in range(max_passes):
        rows = await _extract_rows(page, header_map)
        before = len(dedup)
        for r in rows:
            key = r["opportunity_id"] or f"{r['project']}|||{r['package']}"
            if key.strip("|"):
                dedup.setdefault(key, r)
        gained = len(dedup) - before

        info = await page.evaluate(
            f"""
            () => {{
                const grid = document.querySelector('.ReactVirtualized__Grid.ReactVirtualized__Table__Grid');
                if (!grid) return {{ok:false}};
                const before = grid.scrollTop;
                grid.scrollTop = Math.min(before + {step_px}, grid.scrollHeight - grid.clientHeight);
                return {{ok:true, after: grid.scrollTop, max: grid.scrollHeight - grid.clientHeight}};
            }}
            """
        )
        print(f"  [{tab_name}] pass {i+1}: +{gained} (total {len(dedup)}) scroll {info.get('after')}/{info.get('max')}")
        if not info.get("ok"):
            break
        await page.wait_for_timeout(600)
        if info["after"] == last_scroll and gained == 0:
            stuck += 1
            if stuck >= 2:
                break
        else:
            stuck = 0
        last_scroll = info["after"]
        if info["after"] >= info["max"] - 1 and gained == 0:
            # 再尝试从顶开始覆盖一遍
            await page.evaluate(
                "() => { const g = document.querySelector('.ReactVirtualized__Grid.ReactVirtualized__Table__Grid'); if (g) g.scrollTop = 0; }"
            )
            await page.wait_for_timeout(600)
            rows = await _extract_rows(page, header_map)
            for r in rows:
                key = r["opportunity_id"] or f"{r['project']}|||{r['package']}"
                if key.strip("|"):
                    dedup.setdefault(key, r)
            break
    # 保险再从顶扫一遍
    try:
        await page.evaluate(
            "() => { const g = document.querySelector('.ReactVirtualized__Grid.ReactVirtualized__Table__Grid'); if (g) g.scrollTop = 0; }"
        )
        await page.wait_for_timeout(800)
        rows = await _extract_rows(page, header_map)
        for r in rows:
            key = r["opportunity_id"] or f"{r['project']}|||{r['package']}"
            if key.strip("|"):
                dedup.setdefault(key, r)
    except Exception:
        pass
    return list(dedup.values())


async def _click_tab(page, label: str) -> bool:
    try:
        loc = page.locator(f"div.styled__StyledFilterText-sc-1pa8xbg-8:text('{label}')").first
        if await loc.count() > 0:
            await loc.click()
            await page.wait_for_timeout(3000)
            print(f"  [OK] clicked tab '{label}'")
            return True
    except Exception:
        pass
    return False


async def _ensure_unfiltered(page):
    """
    若见 "Viewing X of your office's Y ..." 提示 → 状态是过滤中，点 "View them all" 一次。
    否则什么都不做（避免重复 toggle）。
    """
    try:
        banner = page.locator("text=/Viewing\\s+\\d+\\s+of your office/")
        cnt = await banner.count()
        if cnt > 0:
            txt = (await banner.first.text_content() or "").strip()
            print(f"  [filter] banner: {txt[:130]}")
            link = page.get_by_text("View them all", exact=False).first
            if await link.count() > 0:
                await link.click()
                await page.wait_for_timeout(3000)
                print("  [OK] toggled filter off — now showing all office opportunities")
        else:
            print("  [filter] no 'Viewing X of Y' banner — assumed already unfiltered")
    except Exception as e:
        print(f"  [filter] err: {e}")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _pending_project_slugs() -> set[str]:
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


def _is_dc_area(location: str, tabs: list[str] | None = None) -> bool:
    """
    判断是否属于 DC/MD/VA 服务范围。
    - 有明确 location 且含关键字 → True
    - 空 location 且 tab 含 Accepted → True（Kyle 已接受过，默认视为 in-scope）
    - 其它 → False
    """
    loc = (location or "").lower()
    if loc:
        return any(kw in loc for kw in IN_SCOPE_KEYWORDS)
    if tabs and "Accepted" in tabs:
        return True
    return False


async def run():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"[ERROR] CDP 连接失败 ({CDP_URL}): {e}")
            return 1

        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "buildingconnected" in (pg.url or "")), None)
        if not page:
            page = context.pages[0] if context.pages else await context.new_page()

        try:
            if "pipeline" not in (page.url or ""):
                await page.goto(PIPELINE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            print(f"[INFO] URL: {page.url}")
            await _ensure_unfiltered(page)

            all_rows: list[dict] = []
            for tab in ["Undecided", "Accepted"]:
                print(f"\n=== Tab: {tab} ===")
                if not await _click_tab(page, tab):
                    print(f"  [SKIP] no tab {tab}")
                    continue
                await _ensure_unfiltered(page)
                items = await _scroll_collect(page, tab)
                for it in items:
                    it["tab"] = tab
                print(f"  [{tab}] 最终 {len(items)} 行")
                all_rows.extend(items)

            # dedup by opportunity_id + tab
            dedup: dict[str, dict] = {}
            for r in all_rows:
                key = f"{r['opportunity_id']}|||{r['tab']}" if r['opportunity_id'] else f"{r['project']}|||{r['package']}|||{r['tab']}"
                dedup.setdefault(key, r)
            rows = list(dedup.values())
            OUT_ROWS.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\n[OUT] {len(rows)} 行 → {OUT_ROWS.name}")

            # 按 opportunity_id 聚合（同一项目若出现在两个 tab 也只算一个）
            proj_map: dict[str, dict] = {}
            for r in rows:
                k = r["opportunity_id"] or _norm(r["project"])
                if k not in proj_map:
                    proj_map[k] = {
                        "opportunity_id": r["opportunity_id"],
                        "project": r["project"],
                        "client": r["client"],
                        "contact": r["contact"],
                        "location": r["location"],
                        "detail_url": r["detail_url"],
                        "due_dates": set(),
                        "packages": [],
                        "tabs": set(),
                        "project_sizes": set(),
                    }
                pm = proj_map[k]
                if r["package"]:
                    pm["packages"].append(r["package"])
                if r["due_date"]:
                    pm["due_dates"].add(r["due_date"])
                if r["project_size"] and r["project_size"] != "–":
                    pm["project_sizes"].add(r["project_size"])
                pm["tabs"].add(r["tab"])
                if not pm["client"] and r["client"]:
                    pm["client"] = r["client"]
                if not pm["contact"] and r["contact"]:
                    pm["contact"] = r["contact"]
                if not pm["location"] and r["location"]:
                    pm["location"] = r["location"]
            projects = [
                {
                    "opportunity_id": p["opportunity_id"],
                    "project": p["project"],
                    "client": p["client"],
                    "contact": p["contact"],
                    "location": p["location"],
                    "detail_url": p["detail_url"],
                    "due_dates": sorted(p["due_dates"]),
                    "packages": p["packages"],
                    "project_sizes": sorted(p["project_sizes"]),
                    "tabs": sorted(p["tabs"]),
                    "in_scope": _is_dc_area(p["location"], sorted(p["tabs"])),
                }
                for p in proj_map.values()
            ]
            OUT_PROJECTS.write_text(json.dumps(projects, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[OUT] {len(projects)} 独立项目 → {OUT_PROJECTS.name}")

            pending = _pending_project_slugs()
            in_scope = [p for p in projects if p["in_scope"]]
            out_scope = [p for p in projects if not p["in_scope"]]
            new_projects = [p for p in in_scope if _norm(p["project"]) not in pending]
            existing = [p for p in in_scope if _norm(p["project"]) in pending]

            lines = []
            lines.append("# BC Bid Board — 待起草项目 (2026-04-17)\n")
            lines.append(
                f"**总计 {len(projects)} 独立项目** | DC/MD/VA 服务范围内 {len(in_scope)} | 范围外 {len(out_scope)} | 已有草稿 {len(existing)} | 🆕 新项目 **{len(new_projects)}**\n"
            )
            lines.append("---\n")
            lines.append("## 🆕 新项目（DC/MD/VA 内，按 due date 升序）\n")
            for p in sorted(new_projects, key=lambda x: x["due_dates"][0] if x["due_dates"] else "9/9/9999"):
                tabs = "/".join(p["tabs"])
                due = p["due_dates"][0] if p["due_dates"] else "—"
                packages = ", ".join(sorted(set([x for x in p["packages"] if x])))[:180]
                lines.append(f"### {p['project']}  <sub>*({tabs} · due {due})*</sub>\n")
                lines.append(f"- **Client (GC)**: {p['client']}")
                lines.append(f"- **Contact**: {p['contact']}")
                lines.append(f"- **Location**: {p['location']}")
                if p["project_sizes"]:
                    lines.append(f"- **Size**: {', '.join(p['project_sizes'])}")
                if packages:
                    lines.append(f"- **Packages invited**: {packages}")
                lines.append(f"- **BC URL**: {p['detail_url']}")
                lines.append(f"- **要不要写 proposal**：[ ] 是  [ ] 跳过  [ ] 已发过")
                lines.append("")

            lines.append("\n---\n")
            lines.append("## 🚫 服务范围外（已跳过，DC/MD/VA 之外）\n")
            for p in out_scope:
                lines.append(f"- {p['project']} — {p['location']}")

            lines.append("\n---\n")
            lines.append("## ✅ 已在 Pending_Approval 里有草稿的（供核对）\n")
            for p in existing:
                lines.append(f"- [{'/'.join(p['tabs'])}] {p['project']} — {p['client']} / {p['contact']}")

            OUT_NEW_MD.write_text("\n".join(lines), encoding="utf-8")
            print(f"[OUT] summary → {OUT_NEW_MD.name}")
            print(f"\n总结: {len(projects)} 独立 | DC/MD/VA 内 {len(in_scope)} | 已有草稿 {len(existing)} | 🆕 新 {len(new_projects)}")

        finally:
            try:
                await browser.close()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
