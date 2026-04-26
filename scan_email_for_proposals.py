"""
扫描 admin@ 和 ycao@buildingcodeconsulting.com（PrivateEmail IMAP）的 Sent + Inbox，
对照 Pending_Approval/Outbound/Proposal_Draft_*.md 的 45 份草稿，判断：

  - sent    : 在 Sent 文件夹找到发往该项目联系人的邮件（按 contact_email 或项目名匹配）
  - replied : 该联系人在 Inbox 有回信
  - none    : 没有发送记录

输出：
  proposal_send_status.json

如果有 ycao@kcyengineer.com 的 IMAP 凭据（.env: KCY_IMAP_USER / KCY_IMAP_PASS / KCY_IMAP_HOST），
一起扫描；没有就跳过，输出提示。
"""
from __future__ import annotations

import csv
import email as _email
import glob
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = BASE_DIR / "proposal_send_status.json"
OUTBOUND = BASE_DIR / "Pending_Approval" / "Outbound"
DAYS_BACK = 120  # 4 个月


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _extract_addr(raw: str) -> str:
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw or "")
    return (m.group(0).lower() if m else (raw or "").lower()).strip()


def _decode_header(raw: str) -> str:
    try:
        parts = _email.header.decode_header(raw or "")
        return " ".join(
            (p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else str(p))
            for p, enc in parts
        )
    except Exception:
        return raw or ""


def _parse_draft(path: Path) -> dict:
    t = path.read_text(encoding="utf-8")
    def grab(label):
        m = re.search(rf"\*\*{re.escape(label)}\*\*\s*\|\s*(.+?)\s*\|", t)
        return (m.group(1).strip() if m else "")
    return {
        "file": path.name,
        "project": grab("Project"),
        "address": grab("Address"),
        "client": grab("Client (GC)") or grab("Client"),
        "contact": grab("Contact"),
        "email": _extract_addr(grab("Email")),
    }


def _load_drafts() -> list[dict]:
    rows = []
    for f in sorted(OUTBOUND.glob("Proposal_Draft_*.md")):
        d = _parse_draft(f)
        if d["project"]:
            rows.append(d)
    return rows


# ── IMAP helpers ────────────────────────────────────────────────────────────
def _imap_connect(host: str, user: str, password: str) -> imaplib.IMAP4_SSL | None:
    try:
        m = imaplib.IMAP4_SSL(host, 993)
        m.login(user, password)
        return m
    except Exception as e:
        print(f"  [IMAP connect failed] {user} @ {host}: {e}")
        return None


def _list_folders(m: imaplib.IMAP4_SSL) -> list[str]:
    try:
        status, data = m.list()
        if status != "OK":
            return []
        out = []
        for raw in data or []:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            # Format: '(\HasNoChildren) "." "INBOX.Sent"'
            m2 = re.search(r'"\." "([^"]+)"', raw)
            if m2:
                out.append(m2.group(1))
            else:
                parts = raw.split(" ")
                if parts:
                    out.append(parts[-1].strip('"'))
        return out
    except Exception:
        return []


def _fetch_since(m: imaplib.IMAP4_SSL, folder: str, days: int) -> list[dict]:
    try:
        status, _ = m.select(f'"{folder}"', readonly=True)
        if status != "OK":
            return []
        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        status, data = m.search(None, f'SINCE "{since}"')
        if status != "OK" or not data[0]:
            return []
        ids = data[0].split()
        out = []
        # batch 50 per fetch
        for i in range(0, len(ids), 50):
            chunk = b",".join(ids[i:i + 50])
            status2, data2 = m.fetch(chunk, "(RFC822.HEADER)")
            if status2 != "OK":
                continue
            for part in data2:
                if not isinstance(part, tuple):
                    continue
                raw = part[1]
                try:
                    msg = _email.message_from_bytes(raw)
                    frm = _decode_header(msg.get("From", ""))
                    to = _decode_header(msg.get("To", ""))
                    cc = _decode_header(msg.get("Cc", ""))
                    subj = _decode_header(msg.get("Subject", ""))
                    date = msg.get("Date", "")
                    out.append({
                        "from": _extract_addr(frm),
                        "to": to,
                        "cc": cc,
                        "subject": subj,
                        "date": date,
                    })
                except Exception:
                    continue
        return out
    except Exception as e:
        print(f"  [fetch err] {folder}: {e}")
        return []


# ── Match logic ────────────────────────────────────────────────────────────
_STOPWORDS = {
    "third", "party", "code", "inspection", "proposal", "building", "consulting",
    "llc", "bcc", "the", "and", "for", "of", "a", "an", "at", "on", "in", "by",
    "washington", "dc", "services", "nw", "ne", "se", "sw", "street", "st",
    "ave", "avenue", "northwest", "northeast", "southeast", "southwest",
    "existing", "conditions", "demo", "demolition", "renovation", "renovations",
    "new", "inc", "company", "re", "fw", "fwd", "project", "from", "upgrade",
    # generic tokens that otherwise overmatch across DC renovations:
    "floor", "floors", "room", "rooms", "suite", "office", "bldg", "blding",
    "center", "centre", "common", "space", "first", "second", "third",
    "fourth", "fifth", "yard", "installation", "replacement", "repair",
}


def _project_keywords(project: str) -> set[str]:
    """从项目名取特征词（去停用词、只留长度 >= 3 的）。"""
    words = re.findall(r"[a-z0-9]+", (project or "").lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def _subject_keywords(subject: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (subject or "").lower())
    return set(words)


def _is_strong_token(w: str) -> bool:
    """长词（>=5 chars）或全数字 4+ 位（像 1724, 1154）= 独特 token。"""
    if len(w) >= 5:
        return True
    if w.isdigit() and len(w) >= 4:
        return True
    return False


def _subject_matches_project(subject: str, project: str) -> bool:
    """
    项目关键词 vs 主题关键词重叠判断：
      - 任一 overlap 词是 strong (>=5 chars 或 4 位数) → match
      - 否则要求 2+ overlap
      - 项目只有 1 关键词 → 任何 overlap 都 match
    """
    pk = _project_keywords(project)
    if not pk:
        return False
    sk = _subject_keywords(subject)
    overlap = pk & sk
    if not overlap:
        return False
    if len(pk) <= 1:
        return True
    # 有 strong token 重叠？
    if any(_is_strong_token(w) for w in overlap):
        return True
    # 否则需要 2+ 重叠
    return len(overlap) >= 2


def _match_sent(drafts: list[dict], sent_msgs: list[dict]) -> dict[str, list]:
    """
    要求：邮件 To 含 contact_email ∧ subject 有项目特征词命中。
    这样一个 contact 的多个项目邮件不会互相误伤。
    """
    hits: dict[str, list] = {}
    for msg in sent_msgs:
        to_addrs = set(re.findall(r"[\w.+-]+@[\w.-]+\.\w+", (msg["to"] or "") + " " + (msg["cc"] or "")))
        to_addrs = {a.lower() for a in to_addrs}
        subj = msg["subject"] or ""
        for d in drafts:
            if not d["email"] or d["email"] not in to_addrs:
                continue
            if _subject_matches_project(subj, d["project"]):
                hits.setdefault(d["file"], []).append({**msg, "_via": "email+subject"})
    return hits


def _match_replies(drafts: list[dict], inbox_msgs: list[dict]) -> dict[str, list]:
    """要求：邮件 From == contact_email ∧ subject 有项目特征词命中。"""
    hits: dict[str, list] = {}
    for msg in inbox_msgs:
        frm = (msg["from"] or "").lower()
        if not frm:
            continue
        subj = msg["subject"] or ""
        for d in drafts:
            if not d["email"] or frm != d["email"]:
                continue
            if _subject_matches_project(subj, d["project"]):
                hits.setdefault(d["file"], []).append(msg)
    return hits


# ── Main ───────────────────────────────────────────────────────────────────
def scan_account(label: str, host: str, user: str, password: str) -> dict:
    print(f"\n===== {label} ({user}) =====")
    m = _imap_connect(host, user, password)
    if not m:
        return {"sent_msgs": [], "inbox_msgs": [], "_error": "connect_failed"}
    folders = _list_folders(m)
    print(f"  folders: {folders}")

    sent_folder = None
    for name in folders:
        low = name.lower()
        if low in ("sent", "inbox.sent", "sent items", "sent messages") or "sent" in low:
            sent_folder = name
            break

    sent = []
    if sent_folder:
        print(f"  [scan] Sent folder: {sent_folder}")
        sent = _fetch_since(m, sent_folder, DAYS_BACK)
        print(f"    got {len(sent)} sent messages (last {DAYS_BACK} days)")
    else:
        print(f"  [warn] no Sent folder found")

    print(f"  [scan] INBOX")
    inbox = _fetch_since(m, "INBOX", DAYS_BACK)
    print(f"    got {len(inbox)} inbox messages (last {DAYS_BACK} days)")

    try:
        m.logout()
    except Exception:
        pass
    return {"sent_msgs": sent, "inbox_msgs": inbox}


def main():
    drafts = _load_drafts()
    print(f"Loaded {len(drafts)} proposal drafts")

    accounts = []
    # PRIV_MAIL1
    u1 = os.environ.get("PRIV_MAIL1_USER", "").strip().strip('"')
    p1 = os.environ.get("PRIV_MAIL1_PASS", "").strip().strip('"')
    h1 = os.environ.get("PRIV_MAIL1_IMAP", "mail.privateemail.com").strip().strip('"')
    if u1 and p1:
        accounts.append(("PRIV_MAIL1", h1, u1, p1))
    # PRIV_MAIL2
    u2 = os.environ.get("PRIV_MAIL2_USER", "").strip().strip('"')
    p2 = os.environ.get("PRIV_MAIL2_PASS", "").strip().strip('"')
    h2 = os.environ.get("PRIV_MAIL2_IMAP", "mail.privateemail.com").strip().strip('"')
    if u2 and p2:
        accounts.append(("PRIV_MAIL2", h2, u2, p2))
    # KCY (optional)
    ku = os.environ.get("KCY_IMAP_USER", "").strip().strip('"')
    kp = os.environ.get("KCY_IMAP_PASS", "").strip().strip('"')
    kh = os.environ.get("KCY_IMAP_HOST", "imap.gmail.com").strip().strip('"')
    if ku and kp:
        accounts.append(("KCY", kh, ku, kp))
    else:
        print("\n[INFO] 未配置 KCY_IMAP_USER/PASS — 跳过 ycao@kcyengineer.com")

    all_sent = []
    all_inbox = []
    per_account = {}
    for (label, host, user, pw) in accounts:
        r = scan_account(label, host, user, pw)
        per_account[label] = {"user": user, "host": host, "sent_count": len(r["sent_msgs"]), "inbox_count": len(r["inbox_msgs"])}
        all_sent.extend([{**x, "_account": label, "_user": user} for x in r["sent_msgs"]])
        all_inbox.extend([{**x, "_account": label, "_user": user} for x in r["inbox_msgs"]])

    print(f"\n[TOTAL] {len(all_sent)} sent, {len(all_inbox)} inbox 累计")

    # match
    sent_hits = _match_sent(drafts, all_sent)
    reply_hits = _match_replies(drafts, all_inbox)

    # compile result
    status = []
    for d in drafts:
        sent_list = sent_hits.get(d["file"], [])
        reply_list = reply_hits.get(d["file"], [])
        if reply_list:
            st = "replied"
        elif sent_list:
            st = "sent"
        else:
            st = "none"
        status.append({
            **d,
            "status": st,
            "sent_count": len(sent_list),
            "sent_samples": [
                {"date": s["date"], "from": s.get("from", ""), "to_snippet": (s["to"] or "")[:60], "subject": (s["subject"] or "")[:90], "account": s["_account"]}
                for s in sent_list[:3]
            ],
            "reply_count": len(reply_list),
            "reply_samples": [
                {"date": r["date"], "from": r.get("from", ""), "subject": (r["subject"] or "")[:90], "account": r["_account"]}
                for r in reply_list[:3]
            ],
        })

    OUT_FILE.write_text(json.dumps({
        "scanned_at": datetime.now().isoformat(),
        "accounts": per_account,
        "days_back": DAYS_BACK,
        "total_drafts": len(drafts),
        "counts_by_status": {
            "sent": sum(1 for s in status if s["status"] == "sent"),
            "replied": sum(1 for s in status if s["status"] == "replied"),
            "none": sum(1 for s in status if s["status"] == "none"),
        },
        "drafts": status,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OUT] {OUT_FILE.name} written")

    # summary
    counts = {"sent": 0, "replied": 0, "none": 0}
    for s in status:
        counts[s["status"]] += 1
    print(f"\n=== 总结 ===")
    print(f"  已发 (sent, no reply yet): {counts['sent']}")
    print(f"  已收到回复 (replied):       {counts['replied']}")
    print(f"  未发 (none):                {counts['none']}")


if __name__ == "__main__":
    main()
