"""
入站回信智能体：监控三个邮箱（Gmail + admin@ + ycao@），分类过滤垃圾，仅处理与建筑/项目/规范咨询相关的回复，
根据 Research_*.md 起草回复草稿，存入 Pending_Approval/Replies/。
"""
import email
import imaplib
import os
import re
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
_env_pending = os.environ.get("PENDING_APPROVAL_DIR", "").strip().strip('"')
PENDING_BASE = Path(_env_pending) if _env_pending else BASE_DIR / "Pending_Approval"
REPLIES_DIR = PENDING_BASE / "Replies"

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# 业务相关关键词（用于判断是否为客户/项目相关，非垃圾）
CLIENT_KEYWORDS = re.compile(
    r"\b(inspection|permit|plan\s*review|code\s*compliance|construction|project|"
    r"building|developer|gc|general\s*contractor|submission|dcra|"
    r"peer\s*review|combo\s*inspection|24[- ]?hour|buildingcodeconsulting)\b",
    re.I,
)
# 垃圾/自动回复特征
SPAM_INDICATORS = re.compile(
    r"\b(unsubscribe|newsletter|no-reply|do not reply|automated|vacation|out of office)\b",
    re.I,
)


def get_mail_accounts():
    """从 .env 读取三个邮箱的 IMAP 配置。"""
    accounts = []
    # Gmail
    u, p = os.environ.get("GMAIL_USER", "").strip(), os.environ.get("GMAIL_APP_PASS", "").strip()
    if u and p:
        accounts.append({"user": u.strip('"'), "pass": p.strip('"'), "host": "imap.gmail.com", "port": 993})
    # Private 1 (admin@)
    u, p = os.environ.get("PRIV_MAIL1_USER", "").strip(), os.environ.get("PRIV_MAIL1_PASS", "").strip()
    if u and p:
        accounts.append({"user": u.strip('"'), "pass": p.strip('"'), "host": "mail.privateemail.com", "port": 993})
    # Private 2 (ycao@)
    u, p = os.environ.get("PRIV_MAIL2_USER", "").strip(), os.environ.get("PRIV_MAIL2_PASS", "").strip()
    if u and p:
        accounts.append({"user": u.strip('"'), "pass": p.strip('"'), "host": "mail.privateemail.com", "port": 993})
    return accounts


def get_body_from_msg(msg) -> str:
    """从 email.message 提取正文。"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True)
            if body:
                body = body.decode(errors="replace")
        except Exception:
            pass
    return (body or "").strip()


def is_likely_client_reply(subject: str, body: str, from_addr: str) -> bool:
    """简单 AI/规则分类：是否与建筑/项目/规范相关，且非垃圾。"""
    if not subject and not body:
        return False
    text = f"{subject} {body} {from_addr}"
    if SPAM_INDICATORS.search(text):
        return False
    if CLIENT_KEYWORDS.search(text):
        return True
    # 若来自已知域名且正文较长，可能是客户回复
    if len(body) > 100 and "@" in from_addr and "no-reply" not in from_addr.lower():
        return True
    return False


def load_research_context() -> str:
    """加载所有 Research_*.md 的摘要，供起草回复时参考。"""
    parts = []
    for p in BASE_DIR.glob("Research_*.md"):
        try:
            t = p.read_text(encoding="utf-8")[:4000]
            parts.append(f"### {p.stem}\n{t}\n")
        except Exception:
            pass
    return "\n".join(parts) if parts else "（暂无 Research 文件）"


def draft_reply(sender: str, subject: str, original_body: str, mailbox: str) -> str:
    """
    根据 Research 背景起草回复草稿（规则 + 占位；可后续接入 Gemini 网页或 API）。
    不包含签名（发件账号已带签名）。
    """
    context = load_research_context()
    to_email = EMAIL_PATTERN.search(sender or "") if sender else None
    to_email = to_email.group(0) if to_email else ""
    safe_from = re.sub(r"[^\w@.-]", "_", (sender or "").strip())[:50]
    draft = (
        f"# 待审批回复\n\n"
        f"**收件人**：{sender}\n"
        f"**邮箱**：{to_email}\n"
        f"**Subject:** Re: {subject[:80]}\n"
        f"**原主题**：{subject}\n"
        f"**检测邮箱**：{mailbox}\n\n"
        f"---\n\n"
        f"**原信摘要**：\n{original_body[:1500]}{'…' if len(original_body) > 1500 else ''}\n\n"
        f"---\n\n"
        f"**建议回复正文**（请根据上下文修改后，将本文件改名为含 -OK 再发送）：\n\n"
        f"Thank you for your reply. I’d be glad to discuss how we can support your project with third-party plan review or 24-hour combo inspections.\n\n"
        f"Could you share a bit more about your timeline and which jurisdiction you’re working with? We can then schedule a short call at your convenience.\n\n"
        f"---\n\n"
        f"*参考 Research 摘要（供编辑时参考）：*\n{context[:2000]}\n"
    )
    return draft


def process_with_ai(sender: str, subject: str, msg, mailbox: str) -> None:
    """分类 + 起草，写入 Pending_Approval/Replies/。"""
    body = get_body_from_msg(msg)
    if not is_likely_client_reply(subject or "", body, sender or ""):
        return
    reply_draft = draft_reply(sender or "", subject or "", body, mailbox)
    REPLIES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w@.-]", "_", (sender or "unknown").strip())[:40]
    draft_path = REPLIES_DIR / f"Reply_to_{safe_name}.md"
    # 若已存在则加时间戳避免覆盖
    if draft_path.exists():
        draft_path = REPLIES_DIR / f"Reply_to_{safe_name}_{int(time.time())}.md"
    draft_path.write_text(reply_draft, encoding="utf-8")
    print(f"  [入站] 已为 {sender} 生成回复草稿: {draft_path.name}")


def check_one_account(acc: dict) -> None:
    try:
        mail = imaplib.IMAP4_SSL(acc["host"], acc.get("port", 993))
        mail.login(acc["user"], acc["pass"])
        mail.select("INBOX")
        _, data = mail.search(None, "UNSEEN")
        for num in data[0].split():
            try:
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                subject = (msg.get("Subject") or "").strip()
                sender = (msg.get("From") or "").strip()
                print(f"  新邮件: {subject[:50]} 来自 {sender}")
                process_with_ai(sender, subject, msg, acc["user"])
            except Exception as e:
                print(f"  处理单封邮件异常: {e}")
        mail.logout()
    except Exception as e:
        print(f"  账号 {acc['user']} 监控异常: {e}")


def check_emails():
    """轮询三个邮箱。"""
    accounts = get_mail_accounts()
    if not accounts:
        print("未配置任一邮箱（GMAIL_USER/PRIV_MAIL1/PRIV_MAIL2），跳过入站监控。")
        return
    for acc in accounts:
        check_one_account(acc)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="入站回信监控：三邮箱 → 分类 → 起草回复到 Pending_Approval/Replies/")
    ap.add_argument("--once", action="store_true", help="只执行一次后退出")
    ap.add_argument("--interval", type=int, default=600, help="轮询间隔秒数，默认 600（10 分钟）")
    args = ap.parse_args()
    if args.once:
        check_emails()
        return
    print(f"入站监控已启动，每 {args.interval} 秒检查三个邮箱。Ctrl+C 退出。")
    while True:
        check_emails()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
