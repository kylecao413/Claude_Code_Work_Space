"""
基于 Word 模板生成 DC 第三方检测服务提案，并按定价逻辑计算 Combo Inspection 单价。
输出到 ../Projects/[Client Name]/[Project Name]/；可选在终端打印定价摘要表供 Yue 确认后再生成。
"""
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
# 项目数据区；模板优先使用 Building Code Consulting 根目录下你提供的模板
PROJECTS_ROOT = BASE_DIR.parent / "Projects"
TEMPLATE_DIR = BASE_DIR / "BuildingConnected" / "templates"
# 你提供的模板路径（Building Code Consulting 根目录）
TEMPLATE_CODE_COMPLIANCE = Path(r"c:\Users\Kyle Cao\DC Business\Building Code Consulting\DC Code Compliance Proposal Template.docx")
TEMPLATE_PLAN_REVIEW = Path(r"c:\Users\Kyle Cao\DC Business\Building Code Consulting\DC Plan Review Proposal Template.docx")
# 回退：本地 templates 目录
DEFAULT_TEMPLATE = TEMPLATE_DIR / "DC Code Compliance Proposal Template.docx"


def get_template_path(template_type: str = "code_compliance") -> Path:
    """优先使用你提供的模板路径，否则回退到 BuildingConnected/templates/。"""
    if template_type == "plan_review":
        if TEMPLATE_PLAN_REVIEW.exists():
            return TEMPLATE_PLAN_REVIEW
        return TEMPLATE_DIR / "DC Plan Review Proposal Template.docx"
    if TEMPLATE_CODE_COMPLIANCE.exists():
        return TEMPLATE_CODE_COMPLIANCE
    return DEFAULT_TEMPLATE

# 定价逻辑（$/visit Combo Inspection）
PRICING_TIERS = {
    "key_large": 295,      # 极大型项目/大客户
    "regular": (300, 350), # 常规/中型回头客
    "small_repeat": (350, 375),  # 小型重复客户
    "one_time": (375, 400),      # 罕见/一次性客户
}


def sanitize_dirname(s: str) -> str:
    """用于生成 Client/Project 文件夹名的安全字符串。"""
    s = re.sub(r'[<>:"/\\|?*]', "_", (s or "").strip())
    return s[:80].strip(" .") or "Unknown"


def suggest_tier(project: dict) -> tuple[str, int, str]:
    """
    根据项目信息建议定价档位与单价，及理由。
    project 可含: client, name, size_sqft, is_repeat, is_key_account 等。
    """
    client = (project.get("client") or "").strip()
    name = (project.get("name") or "").strip()
    size = project.get("size_sqft") or project.get("scope_notes") or ""
    is_repeat = project.get("is_repeat", False)
    is_key = project.get("is_key_account", False)
    # 极大型/大客户
    if is_key or (size and "large" in str(size).lower()) or ("marriott" in name.lower() or "flagship" in name.lower()):
        return "key_large", PRICING_TIERS["key_large"], "极大型/大客户 $295/visit"
    # 常规/中型回头客
    if is_repeat and not client.startswith("Small"):
        return "regular", (PRICING_TIERS["regular"][0] + PRICING_TIERS["regular"][1]) // 2, "常规/中型回头客 $300–350/visit"
    # 小型重复
    if is_repeat:
        return "small_repeat", (PRICING_TIERS["small_repeat"][0] + PRICING_TIERS["small_repeat"][1]) // 2, "小型重复客户 $350–375/visit"
    # 一次性
    return "one_time", (PRICING_TIERS["one_time"][0] + PRICING_TIERS["one_time"][1]) // 2, "一次性客户 $375–400/visit"


def print_pricing_summary(project: dict, tier: str, price_per_visit: int, reason: str, est_visits: int = 12):
    """在终端打印定价摘要表，供 Yue 手机回复「同意」或修改。"""
    total = price_per_visit * est_visits
    print("\n" + "=" * 60)
    print("定价摘要（请确认或回复修改）")
    print("=" * 60)
    print(f"  项目: {project.get('name', 'N/A')}")
    print(f"  客户: {project.get('client', 'N/A')}")
    print(f"  档位: {tier} | 理由: {reason}")
    print(f"  建议单价: ${price_per_visit}/visit (Combo Inspection)")
    print(f"  预估次数: {est_visits} visits → 合计约 ${total}")
    print("=" * 60)
    print("回复「同意」将按此生成提案；或指定单价如 320 再生成。\n")


def get_proposal_output_dir(client_name: str, project_name: str) -> Path:
    """../Projects/[Client]/[Project]/，不存在则创建。"""
    client = sanitize_dirname(client_name)
    project = sanitize_dirname(project_name)
    out_dir = PROJECTS_ROOT / client / project
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def fill_template(
    template_path: Path,
    out_path: Path,
    project: dict,
    price_per_visit: int,
    est_visits: int = 12,
    scope_notes: str = "",
) -> bool:
    """
    使用 python-docx 打开模板，替换占位符（如 {{Client}}、{{Project}}、{{PricePerVisit}} 等），保存到 out_path。
    """
    try:
        from docx import Document
    except ImportError:
        print("请安装 python-docx: pip install python-docx")
        return False
    if template_path.exists():
        doc = Document(str(template_path))
    else:
        print(f"未找到模板 {template_path}，使用内置简易模板。请将正式模板放入 BuildingConnected/templates/ 以获得正确版式。")
        doc = Document()
        doc.add_paragraph("Third-Party Code Compliance Inspection Proposal")
        doc.add_paragraph("Client: {{Client}}")
        doc.add_paragraph("Project: {{Project}}")
        doc.add_paragraph("Price per visit (Combo): ${{PricePerVisit}}")
        doc.add_paragraph("Estimated visits: {{EstVisits}} | Total: ${{Total}}")
        doc.add_paragraph("Scope: {{ScopeNotes}}")
        doc.add_paragraph("Building Code Consulting LLC – DC Third-Party agency. Yue Cao (PE, MCP).")
    total = price_per_visit * est_visits
    today = datetime.now().strftime("%m-%d-%Y")
    replacements = {
        # Existing placeholders
        "{{Client}}": project.get("client", ""),
        "{{Project}}": project.get("name", ""),
        "{{ProjectName}}": project.get("name", ""),
        "{{Attention}}": project.get("attention", project.get("contact_name", "")),
        "{{Address}}": project.get("address", ""),
        "{{ProjectAddress}}": project.get("address", ""),
        "{{ContactName}}": project.get("attention", project.get("contact_name", "")),
        "{{ContactEmail}}": project.get("contact_email", ""),
        "{{PricePerVisit}}": str(price_per_visit),
        "{{EstVisits}}": str(est_visits),
        "{{Total}}": str(total),
        "{{ScopeNotes}}": scope_notes or project.get("description", "")[:2000],
        "{{BuildingCodeConsulting}}": "Building Code Consulting LLC",
        "{{DC Third-Party}}": "DC Third-Party agency",
        "{{Yue Cao}}": "Yue Cao (PE, MCP)",
        "{{Date}}": today,
        "{{DateLong}}": datetime.now().strftime("%B %d, %Y"),
        # Template leftovers (hardcoded old-project values in the .docx)
        "Insomnia Cookies Renovation": project.get("name", ""),
        "Insomnia Cookies": project.get("name", ""),
        "Cox & Company, LLC": project.get("client", ""),
        "Cox & Company": project.get("client", ""),
        "Bryan Kerr": project.get("attention", project.get("contact_name", "")),
        "701 Monroe Street NE": project.get("address", ""),
        "701 Monroe ST NE": project.get("address", ""),
        "701 Monroe": project.get("address", ""),
        "01-12-2026": today,
        "01/12/2026": today,
    }

    def replace_in_paragraph(para):
        for run in para.runs:
            for k, v in replacements.items():
                if k in run.text:
                    run.text = run.text.replace(k, str(v))

    # First pass: run-level replacement
    for p in doc.paragraphs:
        replace_in_paragraph(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_in_paragraph(p)

    # Second pass: paragraph-level replace to catch text split across runs
    for p in doc.paragraphs:
        full = p.text
        changed = False
        for find_str, repl in replacements.items():
            if find_str in full:
                full = full.replace(find_str, str(repl))
                changed = True
        if changed:
            p.clear()
            p.add_run(full)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    full = p.text
                    changed = False
                    for find_str, repl in replacements.items():
                        if find_str in full:
                            full = full.replace(find_str, str(repl))
                            changed = True
                    if changed:
                        p.clear()
                        p.add_run(full)

    # Third pass: fix paragraphs with stubborn split-run values
    for p in doc.paragraphs:
        full = p.text
        if "tenant fit out" in full and "AHUs" in full:
            # Old Insomnia Cookies Exhibit A description — replace entirely
            p.clear()
            p.add_run(scope_notes or project.get("description", ""))
        elif full.strip() == "Washington DC":
            p.clear()
            p.add_run(project.get("address", "Washington, DC"))
        elif "01-12-2026" in full or full.strip() == "01/12/2026":
            p.clear()
            p.add_run(today)
        elif "Flat rate of $325" in full or "(Flat rate of $325" in full:
            p.clear()
            p.add_run(f"Inspection Services Estimated: (Flat rate of ${price_per_visit}/visit)")

    set_all_text_black(doc)
    doc.save(str(out_path))
    return True


def set_all_text_black(doc) -> None:
    """将文档中所有 run 的字体设为黑色，消除红色占位符。"""
    try:
        from docx.shared import RGBColor
    except ImportError:
        return
    black = RGBColor(0, 0, 0)
    for p in doc.paragraphs:
        for run in p.runs:
            run.font.color.rgb = black
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.color.rgb = black
    for section in doc.sections:
        for header_footer in (section.header, section.footer):
            for p in header_footer.paragraphs:
                for run in p.runs:
                    run.font.color.rgb = black


def create_email_draft(client_name: str, project_name: str, proposal_path: Path, to_email: str = "") -> Path:
    """在 Pending_Approval/Outbound/ 下创建发送提案的邮件草稿。"""
    outbound = BASE_DIR / "Pending_Approval" / "Outbound"
    outbound.mkdir(parents=True, exist_ok=True)
    safe = sanitize_dirname(project_name).replace(" ", "_")
    draft_path = outbound / f"BC_Proposal_{safe}_Draft.md"
    body = f"""**收件人**：{to_email or '(请填写 BC 项目联系人邮箱)'}
**邮箱**：（请填写）
**Subject:** Third-Party Code Compliance Inspection Proposal – {project_name}

---

Building Code Consulting LLC 已根据项目信息准备好 DC 第三方检测服务提案，见附件。

Please find attached our proposal for Third-Party Code Compliance Inspection services for {project_name}. We are a DC Third-Party agency; Yue Cao (PE, MCP) will oversee code compliance and inspection coordination.

Best regards,
Yue Cao, PE, MCP
Building Code Consulting
"""
    draft_path.write_text(
        f"# 邮件草稿：BuildingConnected 提案 – {project_name}\n\n"
        f"**附件**：{proposal_path.name}\n\n"
        + body,
        encoding="utf-8",
    )
    return draft_path


def docx_to_pdf(docx_path: Path) -> Path | None:
    """
    将生成的 .docx 转为同目录下的 .pdf（Windows 下使用 docx2pdf/Word COM）。
    返回 PDF 路径，失败返回 None。
    """
    if not docx_path or not Path(docx_path).exists():
        return None
    docx_path = Path(docx_path)
    pdf_path = docx_path.with_suffix(".pdf")
    try:
        from docx2pdf import convert
        convert(str(docx_path), str(pdf_path))
        return pdf_path if pdf_path.exists() else None
    except Exception as e:
        print(f"PDF 转换失败 {docx_path}: {e}", file=sys.stderr)
        return None


def run_single_project(
    project: dict,
    price_per_visit: int | None = None,
    est_visits: int = 12,
    skip_confirm: bool = False,
    template_path: Path | None = None,
    template_type: str = "code_compliance",
) -> dict:
    """
    对单个项目：建议定价 → 可选确认 → 填模板 → 输出 Word 到 Projects/Client/Project/ → 写邮件草稿。
    template_type: "code_compliance" | "plan_review"；未传 template_path 时按此选模板。
    返回 { "success", "output_docx", "draft_path", "error" }。
    """
    template_path = template_path or get_template_path(template_type)
    tier, suggested_price, reason = suggest_tier(project)
    price = price_per_visit if price_per_visit is not None else suggested_price
    if not skip_confirm:
        print_pricing_summary(project, tier, price, reason, est_visits)
        # 交互式时可在此等待用户输入「同意」或数字；脚本模式用 skip_confirm=True 直接生成
    out_dir = get_proposal_output_dir(project.get("client", "Unknown"), project.get("name", "Project"))
    docx_name = f"{sanitize_dirname(project.get('name', 'Proposal'))} - Third Party Code Inspection Proposal from BCC.docx"
    out_docx = out_dir / docx_name
    scope = (project.get("description") or "")[:3000]
    ok = fill_template(template_path, out_docx, project, price, est_visits, scope)
    if not ok:
        return {"success": False, "output_docx": "", "draft_path": "", "error": "模板填充失败"}
    draft_path = create_email_draft(
        project.get("client", ""),
        project.get("name", ""),
        out_docx,
        project.get("contact_email", ""),
    )
    return {
        "success": True,
        "output_docx": str(out_docx),
        "draft_path": str(draft_path),
        "error": "",
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="DC 第三方检测/Plan Review 提案生成（Word 模板 + 定价逻辑）")
    ap.add_argument("--client", default="", help="客户名称")
    ap.add_argument("--project", default="", help="项目名称")
    ap.add_argument("--price", type=int, default=None, help="指定单价 $/visit，不填则自动建议")
    ap.add_argument("--visits", type=int, default=12, help="预估检测次数")
    ap.add_argument("--skip-confirm", action="store_true", help="不打印定价表，直接生成")
    ap.add_argument("--template", type=str, default="", help="Word 模板路径（不填则用 --type 选择）")
    ap.add_argument("--type", dest="template_type", choices=("code_compliance", "plan_review"), default="code_compliance", help="使用 Code Compliance 或 Plan Review 模板")
    ap.add_argument("--contact", default="", help="Contact/attention person name")
    ap.add_argument("--address", default="", help="Project address (e.g. '20 F Street NW, Suite 550, Washington, DC 20001')")
    args = ap.parse_args()
    project = {
        "name": args.project or "St. Joseph's on Capitol Hill – Phase I",
        "client": args.client or "Sample Client",
        "attention": args.contact,
        "address": args.address,
        "description": "",
    }
    template_path = Path(args.template) if args.template else None
    result = run_single_project(project, price_per_visit=args.price, est_visits=args.visits, skip_confirm=args.skip_confirm, template_path=template_path, template_type=args.template_type)
    if result["success"]:
        print("提案已生成:", result["output_docx"])
        print("邮件草稿:", result["draft_path"])
    else:
        print("失败:", result.get("error"), file=sys.stderr)
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
