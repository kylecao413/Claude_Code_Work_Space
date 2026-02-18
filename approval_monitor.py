"""
审批监听器：每 10 分钟扫描 Pending_Approval/ 文件夹。
若某草稿被改名为 XXX-OK.md（表示已审批），则解析收件人/主题/正文，用 admin@ 发送并抄送 ycao@，再将文件移至 Sent/ 归档。
适合与 Google Drive / OneDrive 同步：在手机端将文件名改为 -OK 即可触发发送。
"""
import os
import re
import shutil
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

from email_sender import send_from_admin

BASE_DIR = Path(__file__).resolve().parent

# 若 .env 中设置 PENDING_APPROVAL_DIR（例如 Google Drive 内路径），则草稿与审批在该目录，手机可见
_env_pending = os.environ.get("PENDING_APPROVAL_DIR", "").strip().strip('"')
PENDING_DIR = Path(_env_pending) if _env_pending else BASE_DIR / "Pending_Approval"
_env_sent = os.environ.get("SENT_DIR", "").strip().strip('"')
SENT_DIR = Path(_env_sent) if _env_sent else (PENDING_DIR.parent / "Sent" if _env_pending else BASE_DIR / "Sent")

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def parse_draft_content(content: str) -> dict:
    """
    从草稿正文解析：to_email, subject, body_plain。
    约定：**邮箱**：xxx@xxx.com ；**Subject:** 或 Subject: 一行；正文在 --- 之后或 Subject 之后。
    """
    out = {"to_email": "", "subject": "", "body_plain": ""}
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "邮箱" in line or "**To**" in line or ("To:" in line and "@" in line):
            m = EMAIL_PATTERN.search(line)
            if m:
                out["to_email"] = m.group(0)
        if "Subject:" in line or "**Subject:**" in line:
            out["subject"] = line.split(":", 1)[-1].strip().strip("*").strip()
            # 若主题跨行则只取本行
    # 正文：取第一个 --- 之后到文件末尾，或取 Subject 之后到末尾；去掉末尾重复签名块（可选）
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
        else:
            body = parts[-1].strip()
    else:
        body = content
    # 去掉开头的元数据行（收件人、Subject 等）
    for sep in ("**Subject:**", "Subject:", "**邮箱**", "邮箱："):
        if sep in body:
            idx = body.find(sep)
            # 正文从该行之后的下一个换行开始
            rest = body[idx:]
            nl = rest.find("\n")
            if nl != -1:
                body = rest[nl + 1 :].strip()
            else:
                body = ""
            break
    out["body_plain"] = body
    return out


def process_approved_file(path: Path) -> bool:
    """处理一个 -OK.md 文件：解析、发送、移至 Sent/。"""
    content = path.read_text(encoding="utf-8")
    parsed = parse_draft_content(content)
    to_email = parsed["to_email"].strip()
    subject = parsed["subject"].strip()
    body = parsed["body_plain"].strip()

    if not to_email:
        # 尝试从正文中任意位置找第一个邮箱作为收件人
        m = EMAIL_PATTERN.search(content)
        if m:
            to_email = m.group(0)
    if not to_email:
        print(f"  [跳过] 未解析到收件人邮箱: {path.name}")
        return False
    if not subject:
        subject = f"Building Code Consulting – Plan Review & Inspection Support"

    ok, msg = send_from_admin(to_email, subject, body)
    if not ok:
        print(f"  [失败] {path.name}: {msg}")
        return False
    print(f"  [已发送] {path.name} -> {to_email}")

    # Log email sent to work_log.json
    try:
        from core_tools.work_log import mark_email_sent
        # Extract project label from filename: BC_Proposal_<ProjectName>_Draft-OK.md
        stem = Path(path).stem.replace("-OK", "")
        project_label = stem.replace("BC_Proposal_", "").replace("_Draft", "").replace("_", " ")
        mark_email_sent("", project_label, to_email, followup_days=4)
    except Exception:
        pass

    # Write to sent_log.csv for backward compatibility
    try:
        import csv
        from datetime import datetime as _dt
        with open(BASE_DIR / "sent_log.csv", "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([to_email, "", "", subject,
                                     _dt.utcnow().isoformat() + "Z"])
    except Exception:
        pass

    SENT_DIR.mkdir(exist_ok=True)
    dest = SENT_DIR / path.name
    shutil.move(str(path), str(dest))
    return True


def scan_and_process():
    """扫描 Pending_Approval 及其子目录（Outbound/、Replies/）下所有 *-OK.md 并处理。"""
    if not PENDING_DIR.exists():
        return
    for f in PENDING_DIR.rglob("*-OK.md"):
        if f.is_file():
            process_approved_file(f)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="审批监听：扫描 Pending_Approval 中的 -OK.md 并发送后移至 Sent/")
    ap.add_argument("--once", action="store_true", help="仅执行一次扫描后退出")
    ap.add_argument("--interval", type=int, default=10, help="轮询间隔（分钟），默认 10")
    args = ap.parse_args()

    if args.once:
        scan_and_process()
        return

    print(f"审批监听已启动，每 {args.interval} 分钟扫描 Pending_Approval/。将草稿改名为 XXX-OK.md 即可触发发送。Ctrl+C 退出。")
    while True:
        scan_and_process()
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
