"""
Building Code Consulting 批量调研流水线：
1. 读取 leads.csv，筛选 Pre-construction 阶段（Starts in 1-3/4-12/12+ months），取前 5 条。
2. 对其中出现的 GC 与 Developer 公司去重后，调用 deep_search_contacts.py 做深度调研。
3. 生成 Research_[公司名].md，并为每家公司生成 Pending_Approval 草稿（含 2–4 位关键人、个性化邮件草稿）。
4. 估算金额 >= 1000 万美元的项目打上 High Value 标签。
"""
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
LEADS_CSV = BASE_DIR / "leads.csv"
_env_pending = os.environ.get("PENDING_APPROVAL_DIR", "").strip().strip('"')
PENDING_DIR = Path(_env_pending) if _env_pending else BASE_DIR / "Pending_Approval"

# Pre-construction 阶段关键词（ConstructionWire 的 stage 列）
PRE_CONSTRUCTION_STAGE_KEYWORDS = ("starts in", "1-3", "4-12", "12+", "months")

# 主题行随机化，侧重 Third-Party Peer Review 或 24-hour Combo Inspections
SUBJECT_TEMPLATES = [
    "Third-Party Peer Review for {project_name} — Expedite Permit Timeline",
    "24-Hour Combo Inspections for {company_name} DC Projects",
    "Expediting Permit Review for {project_name}",
    "{project_name} — Plan Review & 24-Hour Inspection Support",
    "Optimizing Inspection Schedule for {project_name}",
]
OUTBOUND_SUBDIR = "Outbound"  # 草稿存入 Pending_Approval/Outbound/


def _parse_value_millions(val: str) -> float | None:
    """从 estimated_value 解析出百万美元数，如 '$15M' -> 15, '10' -> 10。"""
    if not val:
        return None
    s = re.sub(r"[$,\s]", "", str(val).strip()).upper()
    if not s:
        return None
    mult = 1.0
    if s.endswith("M") or "MILLION" in s:
        s = re.sub(r"M$|MILLION.*", "", s).strip()
        mult = 1.0
    elif "K" in s or "THOUSAND" in s:
        s = re.sub(r"K$|THOUSAND.*", "", s).strip()
        mult = 0.001
    try:
        return float(s) * mult
    except ValueError:
        return None


def load_leads(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_pre_construction(stage: str) -> bool:
    s = (stage or "").lower()
    return any(k in s for k in PRE_CONSTRUCTION_STAGE_KEYWORDS)


def run_research_for_company(company: str) -> bool:
    """调用 deep_search_contacts.py 对单家公司做深度调研。"""
    cmd = [sys.executable, str(BASE_DIR / "deep_search_contacts.py"), company]
    r = subprocess.run(cmd, cwd=str(BASE_DIR), timeout=120)
    return r.returncode == 0


def add_subject_and_body_to_draft(draft_path: Path, company_name: str, project_name: str, high_value: bool) -> None:
    """
    在已有草稿文件顶部加入：本次选用主题、备选主题、以及简短邮件正文模板（PE/MCP、24 小时检测、项目引用）。
    """
    if not draft_path.exists():
        return
    import random
    chosen = random.choice(SUBJECT_TEMPLATES)
    subject_chosen = chosen.format(project_name=project_name or "[Project Name]", company_name=company_name)
    others = [t.format(project_name=project_name or "[Project Name]", company_name=company_name)
              for t in SUBJECT_TEMPLATES if t != chosen]

    header = (
        f"# 邮件草稿：{company_name}\n\n"
        f"**本次选用主题**：{subject_chosen}\n\n"
        f"**备选主题**：\n"
        + "\n".join(f"- {s}" for s in others) + "\n\n"
        f"**收件人**：（从下方 Research 摘要中填写 2–4 位关键人）\n"
        f"**邮箱**：（请填写收件人邮箱，审批 -OK 后将自动发送）\n"
        f"**发件**：admin@buildingcodeconsulting.com，抄送 ycao@buildingcodeconsulting.com。\n"
    )
    if high_value:
        header += "\n**High Value**（估算金额 ≥ $10M）\n\n"
    header += "---\n\n**邮件正文模板**（可根据 Research 微调）：\n\n"
    body_tpl = (
        f"Hi,\n\n"
        f"I noticed {company_name} is moving forward with {project_name or '[project]'} and similar work in the region. "
        f"For projects of this complexity, permit timing and code compliance are often critical path drivers. "
        f"Third-party peer review can shorten the time to agency approval.\n\n"
        f"I am Kyle Cao, PE (Civil & Electrical) and ICC Master Code Professional (MCP). We support developers and GCs by:\n"
        f"- Third-Party Plan Review & Peer Review: identify issues before submission and expedite jurisdictional review.\n"
        f"- 24-Hour Combo Inspections: full-scope DC inspections with a 24-hour turnaround guarantee.\n\n"
        f"I would welcome a brief conversation to discuss how our pre-submission reviews or inspection support can serve your upcoming projects.\n\n"
        f"Best regards,\nKyle Cao, PE, MCP\nBuilding Code Consulting\n"
    )
    header += body_tpl + "\n---\n\n"

    content = draft_path.read_text(encoding="utf-8")
    if "本次选用主题" in content:
        return
    # 保留原文件中「## Research 摘要」及之后的内容，前面替换为我们生成的主题+正文模板
    if "## Research 摘要" in content:
        rest = content.split("## Research 摘要", 1)[-1].strip()
        rest = "## Research 摘要（可粘贴关键联系人再写邮件）\n\n" + rest
    else:
        rest = content
    new_content = header + rest
    draft_path.write_text(new_content, encoding="utf-8")


def main():
    leads = load_leads(LEADS_CSV)
    if not leads:
        print("leads.csv 为空或不存在。请先运行 ConstructionWire 抓取并导出：")
        print("  python constructionwire_dc_leads.py --pages 2 --export leads.csv")
        return 1

    pre = [l for l in leads if is_pre_construction(l.get("stage", ""))]
    top5 = pre[:5]
    if not top5:
        print("没有处于 Pre-construction 阶段（Starts in 1-3/4-12/12+ months）的 Lead。")
        return 1

    print(f"筛选出 Pre-construction 前 5 条：")
    for i, L in enumerate(top5, 1):
        val = L.get("estimated_value", "")
        v = _parse_value_millions(val)
        tag = " [High Value]" if v is not None and v >= 10 else ""
        print(f"  {i}. {L.get('project_name', '')[:50]} | {L.get('stage', '')} | {val}{tag}")

    companies = set()
    for L in top5:
        for k in ("developer_company", "gc_company"):
            c = (L.get(k) or "").strip()
            if c:
                companies.add(c)

    outbound_dir = PENDING_DIR / OUTBOUND_SUBDIR
    outbound_dir.mkdir(parents=True, exist_ok=True)
    for company in sorted(companies):
        print(f"\n正在调研: {company}")
        ok = run_research_for_company(company)
        if not ok:
            print(f"  跳过后续草稿增强（调研未成功）")
            continue
        # 找到该项目名（用于主题与正文引用）
        project_name = ""
        high_value = False
        for L in top5:
            if L.get("developer_company", "").strip() == company or L.get("gc_company", "").strip() == company:
                project_name = L.get("project_name", "")
                v = _parse_value_millions(L.get("estimated_value", ""))
                if v is not None and v >= 10:
                    high_value = True
                break
        safe_name = re.sub(r"[^\w\s\-]", "", (company or "").strip())
        safe_name = re.sub(r"\s+", "_", safe_name).strip("_") or "Company"
        draft_path = outbound_dir / f"{safe_name}_Draft.md"
        add_subject_and_body_to_draft(draft_path, company, project_name, high_value)
        print(f"  草稿已增强: {draft_path.name}")

    print(f"\n批量调研完成。请审阅 Pending_Approval/{OUTBOUND_SUBDIR}/ 下草稿，将需发送的改为 XXX-OK.md 后由 approval_monitor 或 mobile_sync_manager 发送。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
