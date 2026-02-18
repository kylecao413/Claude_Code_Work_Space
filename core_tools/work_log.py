"""
work_log.py — Persistent work-log for deduplication & follow-up tracking.

Stores state in work_log.json (one entry per project) at the Business Automation root.
Used by proposal_generator.py and approval_monitor.py to record what's been done,
so "Check Inbox" sessions skip already-completed work and surface due follow-ups.

Status progression:
  pending → proposal_done → email_drafted → email_sent → followup_due → closed
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # core_tools/
WORK_LOG_PATH = BASE_DIR.parent / "work_log.json"  # Business Automation/work_log.json


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    """Load work_log.json; return {} if missing or corrupt."""
    if not WORK_LOG_PATH.exists():
        return {}
    try:
        return json.loads(WORK_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(log: dict) -> None:
    """Atomically write work_log.json."""
    WORK_LOG_PATH.write_text(
        json.dumps(log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _today() -> str:
    return date.today().isoformat()   # "YYYY-MM-DD"


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def project_key(client: str, project: str) -> str:
    """Returns canonical key: 'ClientName | ProjectName'."""
    return f"{(client or '').strip()} | {(project or '').strip()}"


def mark_proposal_done(client: str, project: str, docx_path: str) -> None:
    """Record that a proposal .docx has been generated for this project."""
    log = _load()
    key = project_key(client, project)
    entry = log.get(key, {})
    entry.update({
        "client": (client or "").strip(),
        "project": (project or "").strip(),
        "proposal_generated": _today(),
        "proposal_docx": str(docx_path),
        "status": "proposal_done",
    })
    log[key] = entry
    _save(log)


def mark_email_drafted(client: str, project: str, draft_path: str) -> None:
    """Record that an email draft has been created for this project."""
    log = _load()
    key = project_key(client, project)
    entry = log.get(key, {})
    entry.update({
        "client": (client or "").strip(),
        "project": (project or "").strip(),
        "email_drafted": _today(),
        "draft_path": str(draft_path),
        "status": "email_drafted",
    })
    log[key] = entry
    _save(log)


def mark_email_sent(
    client: str,
    project: str,
    contact_email: str,
    followup_days: int = 4,
) -> None:
    """Record that an email was sent; compute next follow-up date."""
    log = _load()
    key = project_key(client, project)
    entry = log.get(key, {})
    sent_date = date.today()
    next_followup = (sent_date + timedelta(days=followup_days)).isoformat()
    entry.update({
        "client": (client or "").strip(),
        "project": (project or "").strip(),
        "email_sent": sent_date.isoformat(),
        "contact_email": (contact_email or "").strip(),
        "followup_days": followup_days,
        "next_followup": next_followup,
        "status": "email_sent",
    })
    log[key] = entry
    _save(log)


def is_proposal_done(client: str, project: str) -> bool:
    """True if a proposal has already been generated for this project."""
    log = _load()
    entry = log.get(project_key(client, project), {})
    return entry.get("status") in ("proposal_done", "email_drafted", "email_sent", "followup_due", "closed")


def is_email_sent_recently(client: str, project: str) -> bool:
    """True if email was sent AND the follow-up date has not yet arrived."""
    log = _load()
    entry = log.get(project_key(client, project), {})
    if entry.get("status") not in ("email_sent",):
        return False
    next_fu = _parse_date(entry.get("next_followup"))
    if next_fu is None:
        return True   # sent but no followup date → treat as recent
    return date.today() < next_fu


def is_followup_due(client: str, project: str) -> bool:
    """True if email was sent and the follow-up date has arrived (or passed)."""
    log = _load()
    entry = log.get(project_key(client, project), {})
    if entry.get("status") not in ("email_sent", "followup_due"):
        return False
    next_fu = _parse_date(entry.get("next_followup"))
    if next_fu is None:
        return False
    return date.today() >= next_fu


def print_status() -> None:
    """Print a markdown-style status table to stdout."""
    log = _load()
    today_str = _today()
    print(f"\n===== Work Log Status ({today_str}) =====")
    if not log:
        print("(no entries yet)")
        print("=" * 44)
        return

    header = f"| {'Project':<45} | {'Status':<14} | {'Sent':<10} | {'Next Followup':<13} |"
    sep    = f"|{'-'*47}|{'-'*16}|{'-'*12}|{'-'*15}|"
    print(header)
    print(sep)

    for key, entry in sorted(log.items()):
        # Auto-update status to followup_due if date has passed
        status = entry.get("status", "pending")
        next_fu = entry.get("next_followup", "")
        if status == "email_sent" and next_fu and date.today() >= date.fromisoformat(next_fu):
            status = "followup_due"

        sent   = entry.get("email_sent", "—")
        nf     = next_fu or "—"
        # Truncate key for display
        display_key = key if len(key) <= 44 else key[:41] + "..."
        print(f"| {display_key:<45} | {status:<14} | {sent:<10} | {nf:<13} |")

    print("=" * 44 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(
        description="Work log CLI — view status or manually mark emails sent."
    )
    ap.add_argument("--status", action="store_true", help="Print status table")
    ap.add_argument(
        "--mark-sent",
        metavar='"Client | Project"',
        help='Mark a project as email_sent. Requires positional <email> argument.',
    )
    ap.add_argument("email", nargs="?", default="", help="Contact email (used with --mark-sent)")
    ap.add_argument("--followup-days", type=int, default=4, help="Days until follow-up (default 4)")
    args = ap.parse_args()

    if args.status:
        print_status()
        return

    if args.mark_sent:
        key = args.mark_sent.strip()
        if " | " in key:
            client, project = key.split(" | ", 1)
        else:
            client, project = "", key
        contact_email = args.email.strip()
        mark_email_sent(client, project, contact_email, followup_days=args.followup_days)
        print(f"Marked as email_sent: {key} → {contact_email}")
        print_status()
        return

    ap.print_help()


if __name__ == "__main__":
    _cli()
