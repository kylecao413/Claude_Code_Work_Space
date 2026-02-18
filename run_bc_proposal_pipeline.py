"""
Pipeline: 检索需提交提案的 BC 项目 → 生成 Word+PDF 到 Projects/Client/Project/ →
生成可点击的列表 → 同步到 Google Drive → 发送 PDF 与 .md 到 Telegram 供外勤审阅。
"""
import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_ROOT = BASE_DIR.parent / "Projects"
INBOX_DIR = BASE_DIR / "Inbox"
PENDING_OUTBOUND = BASE_DIR / "Pending_Approval" / "Outbound"

# 可选：提案副本同步到 Google Drive 的目录（便于手机/外勤审阅）
GDRIVE_PROPOSALS = os.environ.get("GDRIVE_PROPOSALS_DIR", "").strip().strip('"')
if not GDRIVE_PROPOSALS:
    _gd = Path(os.path.expanduser("~")) / "Google Drive" / "My Drive" / "BCC_Proposals_Review"
    GDRIVE_PROPOSALS = str(_gd) if _gd.exists() else ""

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
TELEGRAM_CHAT_IDS = [x.strip() for x in (os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "") or "").split(",") if x.strip()]


def get_projects_needing_proposal(use_scraper: bool = False, fallback_path: Path | None = None):
    """
    若 use_scraper=True：用 BuildingConnected 抓取「需提案且未提交」列表（会打开浏览器，可登录）；
    否则或抓取为空时，从 fallback_path (bc_pending_projects.json) 读取。
    返回 list[dict] 每项含 name, client, description 等。
    """
    fallback_path = fallback_path or BASE_DIR / "bc_pending_projects.json"
    if use_scraper:
        try:
            from buildingconnected_bid_scraper import run as bc_run
            result = asyncio.run(bc_run(headless=False, months_back=3, max_projects=30))
            not_submitted = result.get("not_submitted") or []
            valid = [p for p in not_submitted if (p.get("name") or "").strip()]
            if valid:
                return valid
        except Exception as e:
            print("BC 抓取未返回有效列表，使用本地 fallback:", e)
    if fallback_path.exists():
        with open(fallback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    return []


def run_pipeline(skip_telegram: bool = False, skip_drive: bool = False, use_bc_scraper: bool = False):
    from proposal_generator import run_single_project, docx_to_pdf, sanitize_dirname

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    projects = get_projects_needing_proposal(use_scraper=use_bc_scraper)
    if not projects:
        print("没有待生成提案的项目。可在 bc_pending_projects.json 中配置项目列表。")
        return []

    generated = []
    for i, proj in enumerate(projects, 1):
        name = (proj.get("name") or "").strip() or f"Project_{i}"
        client = (proj.get("client") or "").strip() or "Unknown"
        print(f"[{i}/{len(projects)}] {client} – {name}")
        result = run_single_project(proj, skip_confirm=True)
        if not result.get("success"):
            print("  失败:", result.get("error"))
            continue
        out_docx = Path(result["output_docx"])
        draft_path = Path(result["draft_path"])
        pdf_path = docx_to_pdf(out_docx)
        project_dir = out_docx.parent
        # 在项目目录放一份 Draft.md 便于 Drive/Telegram 一起同步
        draft_in_project = project_dir / "Proposal_Draft.md"
        if draft_path.exists():
            shutil.copy2(draft_path, draft_in_project)
        entry = {
            "client": client,
            "name": name,
            "docx": str(out_docx),
            "pdf": str(pdf_path) if pdf_path else None,
            "draft": str(draft_in_project) if draft_in_project.exists() else str(draft_path),
            "project_dir": str(project_dir),
        }
        generated.append(entry)

        # Google Drive：复制到 GDRIVE_PROPOSALS / Client_Project/
        if not skip_drive and GDRIVE_PROPOSALS:
            drive_dir = Path(GDRIVE_PROPOSALS) / f"{sanitize_dirname(client)}_{sanitize_dirname(name)}"
            drive_dir.mkdir(parents=True, exist_ok=True)
            if out_docx.exists():
                shutil.copy2(out_docx, drive_dir / out_docx.name)
            if pdf_path and pdf_path.exists():
                shutil.copy2(pdf_path, drive_dir / pdf_path.name)
            if draft_in_project.exists():
                shutil.copy2(draft_in_project, drive_dir / "Proposal_Draft.md")
            entry["drive_dir"] = str(drive_dir)

        # Telegram：发送 PDF 和 .md
        if not skip_telegram and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS:
            for chat_id in TELEGRAM_CHAT_IDS:
                if pdf_path and pdf_path.exists():
                    _send_telegram_document(chat_id, pdf_path, f"Proposal – {name}.pdf")
                if draft_in_project.exists():
                    _send_telegram_document(chat_id, draft_in_project, f"Proposal_Draft – {name}.md")

    # 生成带 file:// 链接的列表，便于本地点击打开
    list_path = INBOX_DIR / f"BC_Proposals_Generated_{datetime.now().strftime('%Y-%m-%d_%H%M')}.md"
    lines = [
        "# BuildingConnected 提案已生成 – 待审阅",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"共 {len(generated)} 项。请逐项打开 Word/PDF 审阅，确认后按 Pending_Approval 流程发送。",
        "",
        "## 列表（点击链接打开）",
        "",
    ]
    for g in generated:
        lines.append(f"### {g['client']} – {g['name']}")
        lines.append("")
        docx_uri = Path(g["docx"]).as_uri()
        lines.append(f"- [Word]({docx_uri})")
        if g.get("pdf"):
            lines.append(f"- [PDF]({Path(g['pdf']).as_uri()})")
        lines.append(f"- [邮件草稿]({Path(g['draft']).as_uri()})")
        if g.get("drive_dir"):
            lines.append(f"- 已同步到 Google Drive: `{g['drive_dir']}`")
        lines.append("")
    list_path.write_text("\n".join(lines), encoding="utf-8")
    list_uri = list_path.resolve().as_uri()
    print("\n列表已写入:", list_path)
    print("可点击下方链接打开列表，再在列表中点击各 Word/PDF 链接审阅：")
    print(list_uri)
    return generated


def _send_telegram_document(chat_id: str, file_path: Path, caption: str = ""):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        payload = {"chat_id": chat_id, "caption": caption[:1024]}
        files = {"document": (file_path.name, f, "application/octet-stream")}
        try:
            r = requests.post(url, data=payload, files=files, timeout=60)
            if not r.ok:
                print("Telegram 发送失败:", r.status_code, r.text[:200])
        except Exception as e:
            print("Telegram 发送异常:", e)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="BC 提案 Pipeline：检索 → 生成 Word+PDF → 列表 → Drive + Telegram")
    ap.add_argument("--no-telegram", action="store_true", help="不发送到 Telegram")
    ap.add_argument("--no-drive", action="store_true", help="不同步到 Google Drive")
    ap.add_argument("--bc-live", action="store_true", help="从 BuildingConnected 现场抓取列表（会打开浏览器）")
    args = ap.parse_args()
    run_pipeline(skip_telegram=args.no_telegram, skip_drive=args.no_drive, use_bc_scraper=args.bc_live)
