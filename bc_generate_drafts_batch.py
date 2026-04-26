"""
基于 bc_project_details.json 生成 Proposal_Draft_*.md（仅 markdown draft, 不生成 docx）。
默认 $350/visit × 3 visits, Kyle 在 review 时改。

输出:
  Pending_Approval/Outbound/Proposal_Draft_<slug>.md   (每个项目一份)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IN_FILE = BASE_DIR / "bc_project_details.json"
PENDING_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
TODAY = datetime.now().strftime("%Y-%m-%d %H:%M")


def _slug(name: str) -> str:
    """把项目名转成文件名友好 slug（保留原大小写但替换空格为下划线）。"""
    s = name.strip()
    s = re.sub(r"[\\/:*?\"<>|]", "", s)  # 去 Windows 非法
    s = re.sub(r"\s+", "_", s)
    return s[:120]


def _clean_client(s: str) -> str:
    """BC 里的 client 是 'J&J 2000, Inc. DBA J&J Construction - Corporate HQ'，只保留法人名。"""
    if not s:
        return ""
    # strip trailing ' - Location/Branch' suffix
    return re.sub(r"\s*-\s*[A-Z][A-Za-z &\.,'/]+$", "", s).strip()


def _default_visits(desc: str, project_name: str) -> int:
    """
    默认 3 次。根据描述启发式调整：
      - school / multi-floor / renovations (plural) / NARA / depot / full reno → 4-5
      - single repair / single door / breaker / bollard → 2
      - demolition only → 2
    """
    name = (project_name or "").lower()
    d = (desc or "").lower()
    text = f"{name} {d}"

    # 小任务信号 → 2 visits
    small_signals = [
        "single door", "repair faulty", "circuit breaker",
        "bollard", "access door",
    ]
    if any(s in text for s in small_signals):
        return 2

    # 大项目信号 → 5 visits
    big_signals = [
        "school", "multi-floor", "multi floor", "4th floor", "depot",
        "dining hall", "renovation project", "new construction",
        "museum", "nara",
    ]
    if any(s in text for s in big_signals):
        return 5

    return 3


def generate_draft(detail: dict) -> tuple[str, str]:
    """返回 (slug, markdown_content)."""
    project = detail.get("Project Name", "") or detail.get("_bidboard", {}).get("project", "")
    slug = _slug(project)
    address = detail.get("Location", "") or ""
    client_raw = detail.get("client_company", "") or ""
    client = _clean_client(client_raw)
    contact = detail.get("contact_name", "") or ""
    email = detail.get("contact_email", "") or ""
    phone = detail.get("contact_phone", "") or ""
    due = detail.get("Date Due", "") or (detail.get("_bidboard", {}).get("due_dates", [""])[0] if detail.get("_bidboard") else "")
    desc = detail.get("Project Information", "") or ""
    trade_inst = detail.get("Trade Specific Instructions", "") or ""
    trade_names = detail.get("Trade Name(s)", "") or ""
    bc_url = detail.get("detail_url", "")

    # 如果描述为空，填 placeholder 提示 Kyle
    if not desc.strip():
        desc = f"_(BC 详情页未提供项目描述 — 请手动补充；Trade Name(s): {trade_names})_"

    visits = _default_visits(desc, project)
    price = 350
    total = price * visits

    lines = []
    lines.append(f"# Proposal Draft — {project}\n")
    lines.append(f"**Status**: PENDING REVIEW")
    lines.append(f"**Generated**: {TODAY}")
    lines.append(f"**Source**: BC detail scrape + automated defaults\n")
    lines.append("---\n")
    lines.append("## Project Info\n")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| **Project** | {project} |")
    lines.append(f"| **Address** | {address} |")
    lines.append(f"| **Client (GC)** | {client} |")
    lines.append(f"| **Contact** | {contact} |")
    lines.append(f"| **Email** | {email} |")
    if phone:
        lines.append(f"| **Phone** | {phone} |")
    if due:
        lines.append(f"| **Due Date** | {due} |")
    if bc_url:
        lines.append(f"| **BC URL** | {bc_url} |")
    if trade_names:
        lines.append(f"| **Trade Name(s)** | {trade_names} |")
    lines.append("")
    lines.append("## Project Description\n")
    lines.append(desc)
    if trade_inst and trade_inst.strip():
        lines.append(f"\n**Trade Specific Instructions**: {trade_inst}")
    lines.append("")
    lines.append("## Proposed Scope of Work (BCC)\n")
    lines.append(f"Third-Party Code Inspection Services for {project}.\n")
    lines.append("### Applicable Disciplines")
    lines.append("- **Building**: Applicable per permit set")
    lines.append("- **Mechanical**: Applicable per permit set")
    lines.append("- **Electrical**: Applicable per permit set")
    lines.append("- **Plumbing**: Applicable per permit set")
    lines.append("- **Fire Protection**: Applicable per permit set\n")
    lines.append("### Estimated Inspections\n")
    lines.append("| Inspection Type | Visits |")
    lines.append("|-----------------|--------|")
    lines.append("| Rough-in (MEP, framing) | 1 |")
    lines.append("| Close-in | 1 |")
    lines.append("| Final inspection | 1 |")
    extra = visits - 3
    if extra > 0:
        lines.append(f"| Additional (large/multi-area) | {extra} |")
    elif extra < 0:
        lines.append("| _(small scope — reduced)_ | — |")
    lines.append(f"| **Total Estimated Visits** | **{visits}** |")
    lines.append("")
    lines.append("### Fee Estimate\n")
    lines.append("| Item | Value |")
    lines.append("|------|-------|")
    lines.append(f"| Price per visit | ${price} |")
    lines.append(f"| Estimated visits | {visits} |")
    lines.append(f"| **Estimated Total** | **${total}** |")
    lines.append("\n---\n")
    lines.append("*Reply `OK` to approve | `price 400` to change fee | `visits 5` to change count*")
    return slug, "\n".join(lines)


def main():
    details = json.loads(IN_FILE.read_text(encoding="utf-8"))
    # Dedupe by project name + location
    seen = {}
    for d in details:
        key = (d.get("Project Name", ""), d.get("Location", ""))
        seen.setdefault(key, d)
    uniq = list(seen.values())

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    skipped = []
    for d in uniq:
        slug, content = generate_draft(d)
        out_path = PENDING_DIR / f"Proposal_Draft_{slug}.md"
        if out_path.exists():
            skipped.append(out_path.name)
            continue
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path.name)

    print(f"Written: {len(written)} | Skipped (already exists): {len(skipped)}\n")
    for n in written:
        print(f"  + {n}")
    if skipped:
        print("\nSkipped:")
        for n in skipped:
            print(f"  . {n}")


if __name__ == "__main__":
    main()
