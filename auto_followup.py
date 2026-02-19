"""
auto_followup.py — Automated 4-day follow-up for cold outreach emails.

Reads sent_log.csv, finds contacts who haven't replied after N days (default 4),
and sends a short follow-up email with the same PDF attachment.

Usage:
    python auto_followup.py                   # Check & preview due follow-ups
    python auto_followup.py --send            # Send follow-ups after confirmation
    python auto_followup.py --dry-run         # Preview without sending
    python auto_followup.py --mark-replied <email>  # Mark a contact as replied (no follow-up)
    python auto_followup.py --days 7          # Override interval (default: 4)
    python auto_followup.py --attachment PATH # PDF to attach to follow-ups
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from email_sender import send_from_admin, send_from_admin_with_attachment

BASE_DIR = Path(__file__).resolve().parent
SENT_LOG = BASE_DIR / "sent_log.csv"

# Columns for the upgraded sent_log
FIELDNAMES = ["contact_email", "contact_name", "company", "project", "subject",
              "sent_at", "replied", "followup_sent_at"]


# ── CSV helpers ────────────────────────────────────────────────────────────────

def _load_log() -> list[dict]:
    """Load sent_log.csv, upgrading old 5-column format if needed."""
    if not SENT_LOG.exists():
        return []

    rows = []
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle old 5-column format (no 'project' field):
            #   contact_email, contact_name, company, subject, sent_at
            # New 6-column format:
            #   contact_email, contact_name, company, project, subject, sent_at
            if "project" not in row and "subject" in row:
                # old format: subject is in column 4 (index 3), sent_at in 5
                # We can't reliably infer project from subject, leave as empty
                row["project"] = ""
            # Ensure new tracking columns are present
            row.setdefault("replied", "")
            row.setdefault("followup_sent_at", "")
            rows.append(dict(row))
    return rows


def _save_log(rows: list[dict]) -> None:
    """Write rows back to sent_log.csv with full FIELDNAMES header."""
    with open(SENT_LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _parse_sent_at(ts: str) -> datetime | None:
    """Parse ISO8601 timestamp (with or without tz offset) to UTC datetime."""
    if not ts:
        return None
    try:
        # Python 3.11+ supports fromisoformat with Z; older needs replace
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _extract_project(row: dict) -> str:
    """Return project name, extracting from subject if stored project field is empty."""
    proj = (row.get("project") or "").strip()
    if proj:
        return proj
    # Try to extract from subject: "...Services for PROJECT | Building Code..."
    subj = row.get("subject", "")
    import re
    m = re.search(r"(?:for|—)\s+(.+?)\s*\|", subj)
    if m:
        return m.group(1).strip()
    return subj


# ── Follow-up email ────────────────────────────────────────────────────────────

def _followup_subject(original_subject: str) -> str:
    """Prefix with Re: if not already prefixed."""
    s = original_subject.strip()
    if s.lower().startswith("re:"):
        return s
    return f"Re: {s}"


def _followup_body(contact_name: str, project: str) -> str:
    """Generate a short, warm follow-up email body."""
    first_name = contact_name.split()[0] if contact_name else "there"
    proj_line = f" regarding {project}" if project else ""
    return (
        f"Hi {first_name},\n\n"
        f"I wanted to follow up on my earlier message{proj_line}. "
        f"I understand you're busy, so I'll keep this brief — I'd love to connect "
        f"and see if BCC can be a helpful resource for your upcoming project.\n\n"
        f"If you have any questions or would like to set up a quick call, "
        f"please don't hesitate to reach out. Happy to work around your schedule."
    )


# ── Core logic ─────────────────────────────────────────────────────────────────

def get_due_contacts(rows: list[dict], days: int = 4) -> list[dict]:
    """Return rows that are due for a follow-up (sent N+ days ago, not replied, no followup sent)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    due = []
    for row in rows:
        if row.get("replied", "").strip() in ("1", "true", "yes", "True"):
            continue  # already replied
        if row.get("followup_sent_at", "").strip():
            continue  # already followed up (one follow-up only)
        sent_at = _parse_sent_at(row.get("sent_at", ""))
        if sent_at and sent_at <= cutoff:
            due.append(row)
    return due


def mark_replied(email: str, rows: list[dict]) -> int:
    """Mark all rows matching email as replied. Returns count of rows updated."""
    email = email.strip().lower()
    count = 0
    for row in rows:
        if row.get("contact_email", "").strip().lower() == email:
            row["replied"] = "1"
            count += 1
    return count


def send_followups(
    due: list[dict],
    attachment_path: str = "",
    dry_run: bool = False,
) -> list[dict]:
    """
    Send follow-up emails for each contact in due list.
    Returns list of successfully sent rows (with followup_sent_at filled in).
    """
    sent = []
    for row in due:
        contact_name = row.get("contact_name", "")
        to_email     = row.get("contact_email", "")
        project      = _extract_project(row)
        subject      = _followup_subject(row.get("subject", "Follow-up from BCC"))
        body         = _followup_body(contact_name, project)

        print(f"\n{'─'*50}")
        print(f"TO:      {contact_name} <{to_email}>")
        print(f"COMPANY: {row.get('company', '')}")
        print(f"PROJECT: {project}")
        print(f"SUBJECT: {subject}")
        print(f"BODY:\n")
        for line in body.split("\n"):
            print(f"  {line}")

        if dry_run:
            print("  [dry-run] Not sent.")
            continue

        if attachment_path and os.path.isfile(attachment_path):
            ok, msg = send_from_admin_with_attachment(to_email, subject, body, attachment_path)
        else:
            ok, msg = send_from_admin(to_email, subject, body)

        if ok:
            row["followup_sent_at"] = datetime.now(timezone.utc).isoformat()
            print(f"  OK: sent to {to_email}")
            sent.append(row)
        else:
            print(f"  FAILED: {msg}")

    return sent


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Auto follow-up for cold outreach emails")
    ap.add_argument("--send",        action="store_true", help="Send follow-ups (requires confirmation)")
    ap.add_argument("--dry-run",     action="store_true", help="Preview follow-ups without sending")
    ap.add_argument("--mark-replied", metavar="EMAIL",   help="Mark contact as replied (no follow-up)")
    ap.add_argument("--days",        type=int, default=4, help="Days since first email before following up (default: 4)")
    ap.add_argument("--attachment",  default="",          help="Path to PDF to attach to follow-ups")
    args = ap.parse_args()

    rows = _load_log()
    if not rows:
        print("sent_log.csv is empty or missing. No contacts to process.")
        return 0

    # ── Mark replied ───────────────────────────────────────────────────────────
    if args.mark_replied:
        count = mark_replied(args.mark_replied, rows)
        if count == 0:
            print(f"No contact found with email: {args.mark_replied}")
            return 1
        _save_log(rows)
        print(f"Marked {count} row(s) as replied for: {args.mark_replied}")
        return 0

    # ── Check / send follow-ups ────────────────────────────────────────────────
    due = get_due_contacts(rows, days=args.days)

    if not due:
        print(f"No follow-ups due (checked {len(rows)} contacts, {args.days}-day interval).")
        # Show summary of sent log
        total = len(rows)
        replied = sum(1 for r in rows if r.get("replied", "").strip() in ("1", "true", "yes", "True"))
        followed = sum(1 for r in rows if r.get("followup_sent_at", "").strip())
        print(f"Status: {total} contacts | {replied} replied | {followed} followed up")
        return 0

    print(f"\n{len(due)} contact(s) due for follow-up (sent {args.days}+ days ago, no reply):\n")
    for i, row in enumerate(due, 1):
        sent_at = _parse_sent_at(row.get("sent_at", ""))
        age = (datetime.now(timezone.utc) - sent_at).days if sent_at else "?"
        print(f"  {i}. {row.get('contact_name', '')} <{row.get('contact_email', '')}> "
              f"— {row.get('company', '')} ({age} days ago)")

    if args.dry_run:
        send_followups(due, attachment_path=args.attachment, dry_run=True)
        return 0

    if not args.send:
        print("\nRun with --send to send follow-ups, or --dry-run to preview email bodies.")
        return 0

    # Confirm before sending
    attachment_path = args.attachment.strip()
    if attachment_path and not os.path.isfile(attachment_path):
        print(f"ERROR: Attachment not found: {attachment_path}")
        return 1

    confirm = input(
        f"\nSend {len(due)} follow-up email(s) from admin@buildingcodeconsulting.com? (Y to confirm): "
    ).strip()
    if confirm.upper() != "Y":
        print("Aborted.")
        return 0

    sent = send_followups(due, attachment_path=attachment_path, dry_run=False)
    _save_log(rows)
    print(f"\nDone. Sent {len(sent)}/{len(due)} follow-up(s).")
    if sent:
        print(f"Updated: {SENT_LOG}")
    return 0 if len(sent) == len(due) else 1


if __name__ == "__main__":
    sys.exit(main())
