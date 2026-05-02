"""
Send 13 fresh CW cold outreach drafts (generated 2026-04-24, sent 2026-04-28).
Larry Serota goes via ycao@ (per cold-outreach-optimization memory). Other 12 via admin@.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from email_sender import send_from_admin, send_from_ycao  # noqa: E402
from core_tools.active_operator import operator_lock  # noqa: E402

OUTBOUND = ROOT / "Pending_Approval" / "Outbound"
SENT_LOG = ROOT / "sent_log.csv"

# Larry Serota = ycao@ sender (developer/owner pitch, polished by Kyle)
YCAO_SENDERS = {"larry.serota@transwestern.com"}

DRAFT_FILES = sorted(OUTBOUND.glob("CW_*_20260424_1208.md"))


def parse_cw_draft(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n---\s*\n", text, maxsplit=1)
    if len(parts) < 2:
        raise ValueError(f"No header/body divider in {path.name}")
    header, body = parts[0], parts[1].strip()

    def get(key: str) -> str | None:
        m = re.search(rf"(?im)\*\*{re.escape(key)}:\*\*\s*(.+)", header)
        return m.group(1).strip() if m else None

    to_field = get("TO")
    subject = get("SUBJECT")
    project = get("PROJECT")
    company = re.search(r"^# CW Cold Outreach\s*[—-]\s*(.+)", header, re.M)
    company = company.group(1).strip() if company else "(unknown)"
    role = get("COMPANY ROLE") or "?"

    if not to_field or not subject:
        raise ValueError(f"Missing TO/SUBJECT in {path.name}")

    to_email_match = re.search(r"<([\w\.\-+]+@[\w\.\-]+)>|([\w\.\-+]+@[\w\.\-]+)", to_field)
    to_email = (to_email_match.group(1) or to_email_match.group(2)).lower()
    contact_name = re.sub(r"<.*?>", "", to_field).strip()

    return {
        "draft_path": path,
        "to": to_email,
        "contact_name": contact_name,
        "company": company,
        "role": role,
        "project": project or "",
        "subject": subject,
        "body": body,
    }


def append_sent_log(d: dict, ok: bool, msg: str) -> None:
    """Append to existing sent_log.csv with the standard CW schema."""
    is_new = not SENT_LOG.exists()
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["contact_email", "contact_name", "company", "project",
                        "subject", "sent_at", "replied", "followup_sent_at",
                        "followup_count", "last_followup_at"])
        w.writerow([
            d["to"], d["contact_name"], d["company"], d["project"], d["subject"],
            datetime.now(timezone.utc).isoformat(),
            "", "", "0", "",
        ])


def main():
    drafts = []
    for p in DRAFT_FILES:
        try:
            drafts.append(parse_cw_draft(p))
        except Exception as e:
            print(f"[!] parse {p.name}: {e}")
    if len(drafts) != len(DRAFT_FILES):
        print(f"[!] parsed {len(drafts)} of {len(DRAFT_FILES)}, aborting.")
        return 1

    print(f"\nReady to send {len(drafts)} CW cold outreach emails.\n")
    for d in drafts:
        sender = "ycao@" if d["to"] in YCAO_SENDERS else "admin@"
        print(f"  via {sender}  →  {d['to']:42} | [{d['role']:<15}] {d['subject'][:55]}")
    print()

    sent = 0
    failed = 0
    for d in drafts:
        send_fn = send_from_ycao if d["to"] in YCAO_SENDERS else send_from_admin
        sender_label = "ycao@" if d["to"] in YCAO_SENDERS else "admin@"
        print(f"\n[SEND via {sender_label}] {d['to']}  |  {d['subject'][:70]}")
        try:
            ok, msg = send_fn(
                to_email=d["to"],
                subject=d["subject"],
                body_plain=d["body"],
            )
        except Exception as e:
            ok, msg = False, f"Exception: {e}"
        print(f"   result: {'OK' if ok else 'FAIL'} — {msg}")
        if ok:
            sent += 1
            append_sent_log(d, ok, msg)
            new_name = d["draft_path"].with_name(d["draft_path"].stem + "-SENT.md")
            d["draft_path"].rename(new_name)
            print(f"   renamed → {new_name.name}")
        else:
            failed += 1
        time.sleep(2)

    print(f"\n=== Done. Sent={sent}, Failed={failed} ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    with operator_lock("send_cw_batch_20260428.py"):
        sys.exit(main())
