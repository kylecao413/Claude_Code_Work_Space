"""
phone_tracker.py — Phone call follow-up tracker for BCC outreach.

Maintains phone_log.csv with call status for all outbound contacts.
Works alongside sent_log.csv (email tracking) and daily_sender.py.

Usage:
    python phone_tracker.py                      # List all contacts due for a call today
    python phone_tracker.py --all                # List ALL contacts (regardless of due date)
    python phone_tracker.py --seed               # (Re)populate phone_log from outbound drafts + sent_log
    python phone_tracker.py --add-phone EMAIL PHONE   # Add/update phone number
    python phone_tracker.py --no-answer EMAIL         # Mark no-answer → schedule follow-up in 2 days
    python phone_tracker.py --no-answer EMAIL --days 3  # Schedule in 3 days instead
    python phone_tracker.py --declined EMAIL     # Mark declined → stop contacting for this project
    python phone_tracker.py --connected EMAIL    # Mark connected (spoke to them)
    python phone_tracker.py --export             # Print full call list as a formatted table
    python phone_tracker.py --stats              # Summary stats
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR     = Path(__file__).resolve().parent
OUTBOUND_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
SENT_LOG     = BASE_DIR / "sent_log.csv"
PHONE_LOG    = BASE_DIR / "phone_log.csv"

FIELDNAMES = [
    "contact_name", "company", "email", "phone",
    "project", "email_sent_date",
    "last_call_date", "call_status", "next_call_date", "notes",
]

# call_status values
STATUS_NOT_CALLED = "not_called"
STATUS_NO_ANSWER  = "no_answer"
STATUS_DECLINED   = "declined"       # STOP — do not contact again for this project
STATUS_CONNECTED  = "connected"      # Spoke to them


# ── CSV helpers ───────────────────────────────────────────────────────────────
def _load_log() -> list[dict]:
    if not PHONE_LOG.exists():
        return []
    with open(PHONE_LOG, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_log(rows: list[dict]) -> None:
    with open(PHONE_LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _find_row(rows: list[dict], email: str) -> int | None:
    """Return index of row matching email (case-insensitive), or None."""
    el = email.strip().lower()
    for i, r in enumerate(rows):
        if r.get("email", "").strip().lower() == el:
            return i
    return None


# ── Sent log helper ──────────────────────────────────────────────────────────
def _load_sent_dates() -> dict[str, str]:
    """Return {email_lower: sent_at_iso} from sent_log.csv."""
    if not SENT_LOG.exists():
        return {}
    result: dict[str, str] = {}
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            e = row.get("contact_email", "").strip().lower()
            d = row.get("sent_at", "").strip()
            if e and d:
                result[e] = d[:10]   # keep YYYY-MM-DD only
    return result


# ── Draft parser (same logic as daily_sender.py) ─────────────────────────────
def _parse_draft(fpath: Path) -> dict | None:
    try:
        text = fpath.read_text(encoding="utf-8")
    except Exception:
        return None

    to_m      = re.search(r"\*\*TO:\*\*\s*(.+?)(?:\n|$)", text)
    subj_m    = re.search(r"\*\*SUBJECT:\*\*\s*(.+?)(?:\n|$)", text)
    project_m = re.search(r"\*\*PROJECT:\*\*\s*(.+?)(?:\n|$)", text)
    company_m = re.search(r"# CW Cold Outreach — (.+?)(?:\n|$)", text)
    phone_m   = re.search(r"\*\*PHONE:\*\*\s*(.+?)(?:\n|$)", text)

    if not to_m:
        return None

    to_raw = to_m.group(1).strip()
    email_m = re.search(r"<(.+?)>", to_raw)
    to_email = email_m.group(1).strip() if email_m else to_raw
    contact_name = to_raw.split("<")[0].strip() if "<" in to_raw else ""

    phone_raw = phone_m.group(1).strip() if phone_m else ""
    phone = "" if phone_raw in ("—", "-", "N/A", "") else phone_raw

    if not to_email or "@" not in to_email:
        return None

    return {
        "contact_name": contact_name,
        "company":      (company_m.group(1).strip() if company_m else fpath.stem),
        "email":        to_email,
        "phone":        phone,
        "project":      (project_m.group(1).strip() if project_m else ""),
    }


# ── Seed ──────────────────────────────────────────────────────────────────────
def cmd_seed(args: argparse.Namespace) -> int:
    """
    Populate phone_log.csv from all outbound CW_*.md drafts.
    Existing rows are preserved; new contacts are added with status=not_called.
    Phone numbers from existing rows are NOT overwritten.
    """
    existing = _load_log()
    existing_emails = {r["email"].strip().lower() for r in existing}
    sent_dates = _load_sent_dates()

    drafts = sorted(OUTBOUND_DIR.glob("CW_*.md"))
    added = 0
    for fpath in drafts:
        d = _parse_draft(fpath)
        if not d:
            continue
        el = d["email"].lower()
        if el in existing_emails:
            # Update email_sent_date if it's now available
            idx = _find_row(existing, d["email"])
            if idx is not None and not existing[idx].get("email_sent_date"):
                existing[idx]["email_sent_date"] = sent_dates.get(el, "")
            continue

        existing.append({
            "contact_name":   d["contact_name"],
            "company":        d["company"],
            "email":          d["email"],
            "phone":          d["phone"],
            "project":        d["project"],
            "email_sent_date": sent_dates.get(el, ""),
            "last_call_date": "",
            "call_status":    STATUS_NOT_CALLED,
            "next_call_date": "",
            "notes":          "",
        })
        existing_emails.add(el)
        added += 1

    _save_log(existing)
    print(f"Seeded phone_log.csv — {added} new contacts added, {len(existing)} total.")
    return 0


# ── Add phone ─────────────────────────────────────────────────────────────────
def cmd_add_phone(email: str, phone: str) -> int:
    rows = _load_log()
    idx = _find_row(rows, email)
    if idx is None:
        print(f"Contact not found: {email}")
        print("Run --seed first, or check spelling.")
        return 1
    rows[idx]["phone"] = phone.strip()
    _save_log(rows)
    print(f"Phone updated for {rows[idx]['contact_name']} ({rows[idx]['company']}): {phone}")
    return 0


# ── Mark no-answer ────────────────────────────────────────────────────────────
def cmd_no_answer(email: str, days: int) -> int:
    rows = _load_log()
    idx = _find_row(rows, email)
    if idx is None:
        print(f"Contact not found: {email}")
        return 1
    today = date.today()
    next_call = (today + timedelta(days=days)).isoformat()
    rows[idx]["call_status"]    = STATUS_NO_ANSWER
    rows[idx]["last_call_date"] = today.isoformat()
    rows[idx]["next_call_date"] = next_call
    _save_log(rows)
    r = rows[idx]
    print(f"Marked NO ANSWER: {r['contact_name']} ({r['company']})")
    print(f"Next follow-up scheduled: {next_call} (in {days} day{'s' if days != 1 else ''})")
    return 0


# ── Mark declined ─────────────────────────────────────────────────────────────
def cmd_declined(email: str, notes: str = "") -> int:
    rows = _load_log()
    idx = _find_row(rows, email)
    if idx is None:
        print(f"Contact not found: {email}")
        return 1
    rows[idx]["call_status"]    = STATUS_DECLINED
    rows[idx]["last_call_date"] = date.today().isoformat()
    rows[idx]["next_call_date"] = ""
    if notes:
        rows[idx]["notes"] = notes
    _save_log(rows)
    r = rows[idx]
    print(f"Marked DECLINED: {r['contact_name']} ({r['company']}) — will not contact again for this project.")
    return 0


# ── Mark connected ────────────────────────────────────────────────────────────
def cmd_connected(email: str, notes: str = "") -> int:
    rows = _load_log()
    idx = _find_row(rows, email)
    if idx is None:
        print(f"Contact not found: {email}")
        return 1
    rows[idx]["call_status"]    = STATUS_CONNECTED
    rows[idx]["last_call_date"] = date.today().isoformat()
    rows[idx]["next_call_date"] = ""
    if notes:
        rows[idx]["notes"] = notes
    _save_log(rows)
    r = rows[idx]
    print(f"Marked CONNECTED: {r['contact_name']} ({r['company']})")
    return 0


# ── List due ──────────────────────────────────────────────────────────────────
def get_due_contacts(rows: list[dict], show_all: bool = False) -> list[dict]:
    """
    Return contacts that are due for a call today.
    - status = not_called (have email, need first call)
    - status = no_answer AND next_call_date <= today
    Excludes: declined, connected.
    If show_all=True, returns all non-declined, non-connected contacts.
    """
    today = date.today().isoformat()
    due = []
    for r in rows:
        status = r.get("call_status", STATUS_NOT_CALLED)
        if status in (STATUS_DECLINED, STATUS_CONNECTED):
            continue
        if show_all:
            due.append(r)
            continue
        if status == STATUS_NOT_CALLED:
            # Only list if email has been sent
            if r.get("email_sent_date"):
                due.append(r)
        elif status == STATUS_NO_ANSWER:
            next_call = r.get("next_call_date", "")
            if not next_call or next_call <= today:
                due.append(r)
    return due


def cmd_list(show_all: bool = False) -> int:
    rows = _load_log()
    if not rows:
        print("phone_log.csv is empty. Run --seed first.")
        return 1

    due = get_due_contacts(rows, show_all=show_all)

    label = "All contacts" if show_all else "Contacts due for a call today"
    print(f"\n{'='*75}")
    print(f"{label} — {date.today().isoformat()}")
    print(f"{'='*75}")

    if not due:
        if show_all:
            print("No contacts in phone_log.csv.")
        else:
            print("No calls due today.")
            no_phone = [r for r in rows if not r.get("phone") and r.get("email_sent_date")
                        and r.get("call_status") not in (STATUS_DECLINED, STATUS_CONNECTED)]
            if no_phone:
                print(f"\n({len(no_phone)} contacts have been emailed but have no phone number recorded.)")
                print("Add phones with: python phone_tracker.py --add-phone EMAIL PHONE")
        return 0

    no_phone_count = 0
    for i, r in enumerate(due, 1):
        phone  = r.get("phone", "") or "(no phone)"
        status = r.get("call_status", STATUS_NOT_CALLED)
        last   = r.get("last_call_date", "") or "never called"
        sent   = r.get("email_sent_date", "") or "not sent"
        next_c = r.get("next_call_date", "")
        notes  = r.get("notes", "")

        status_tag = {
            STATUS_NOT_CALLED: "FIRST CALL",
            STATUS_NO_ANSWER:  f"NO ANSWER (last: {last})",
        }.get(status, status.upper())

        if not r.get("phone"):
            no_phone_count += 1

        print(f"\n  {i:>3}. {r['contact_name']} — {r['company']}")
        print(f"       Phone:   {phone}")
        print(f"       Email:   {r.get('email','')}")
        print(f"       Project: {r.get('project','')[:70]}")
        print(f"       Status:  {status_tag}")
        print(f"       Email sent: {sent}")
        if next_c:
            print(f"       Scheduled: {next_c}")
        if notes:
            print(f"       Notes:   {notes}")

    print(f"\n{'─'*75}")
    print(f"Total due: {len(due)}")
    if no_phone_count:
        print(f"Missing phone: {no_phone_count} contacts — add with: python phone_tracker.py --add-phone EMAIL PHONE")
    return 0


# ── Export table ──────────────────────────────────────────────────────────────
def cmd_export() -> int:
    rows = _load_log()
    if not rows:
        print("phone_log.csv is empty. Run --seed first.")
        return 1

    # Only rows where email has been sent (actionable)
    actionable = [r for r in rows if r.get("email_sent_date")]
    print(f"\n{'='*100}")
    print(f"{'#':<4} {'Name':<30} {'Company':<32} {'Phone':<18} {'Status':<14} {'Email Sent'}")
    print(f"{'─'*100}")
    for i, r in enumerate(actionable, 1):
        phone  = r.get("phone") or "—"
        status = r.get("call_status", STATUS_NOT_CALLED)
        sent   = r.get("email_sent_date", "")[:10]
        print(f"{i:<4} {r['contact_name']:<30} {r['company']:<32} {phone:<18} {status:<14} {sent}")
    print(f"{'─'*100}")
    print(f"Total emailed: {len(actionable)}")
    return 0


# ── Stats ─────────────────────────────────────────────────────────────────────
def cmd_stats() -> int:
    rows = _load_log()
    if not rows:
        print("phone_log.csv is empty.")
        return 1

    total      = len(rows)
    emailed    = sum(1 for r in rows if r.get("email_sent_date"))
    has_phone  = sum(1 for r in rows if r.get("phone"))
    not_called = sum(1 for r in rows if r.get("call_status") == STATUS_NOT_CALLED)
    no_answer  = sum(1 for r in rows if r.get("call_status") == STATUS_NO_ANSWER)
    declined   = sum(1 for r in rows if r.get("call_status") == STATUS_DECLINED)
    connected  = sum(1 for r in rows if r.get("call_status") == STATUS_CONNECTED)
    due_today  = len(get_due_contacts(rows))

    print(f"\n{'='*50}")
    print(f"Phone Tracker Stats — {date.today().isoformat()}")
    print(f"{'='*50}")
    print(f"  Total contacts:   {total}")
    print(f"  Emailed:          {emailed}")
    print(f"  Have phone #:     {has_phone}")
    print(f"  ─────────────────────────────")
    print(f"  Not called yet:   {not_called}")
    print(f"  No answer:        {no_answer}")
    print(f"  Declined:         {declined}  (do not contact)")
    print(f"  Connected:        {connected}")
    print(f"  ─────────────────────────────")
    print(f"  Due for call today: {due_today}")
    return 0


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Phone call follow-up tracker for BCC outreach")
    ap.add_argument("--seed",       action="store_true",  help="Populate phone_log from outbound drafts")
    ap.add_argument("--all",        action="store_true",  help="List ALL contacts (not just due today)")
    ap.add_argument("--add-phone",  nargs=2, metavar=("EMAIL", "PHONE"), help="Add/update phone for contact")
    ap.add_argument("--no-answer",  metavar="EMAIL",      help="Mark no-answer, schedule follow-up")
    ap.add_argument("--days",       type=int, default=2,  help="Days until next follow-up (default: 2)")
    ap.add_argument("--declined",   metavar="EMAIL",      help="Mark declined — stop contacting")
    ap.add_argument("--connected",  metavar="EMAIL",      help="Mark connected (spoke to them)")
    ap.add_argument("--notes",      default="",           help="Optional notes for --declined/--connected")
    ap.add_argument("--export",     action="store_true",  help="Print full call list table")
    ap.add_argument("--stats",      action="store_true",  help="Show summary statistics")
    args = ap.parse_args()

    if args.seed:
        return cmd_seed(args)
    if args.add_phone:
        return cmd_add_phone(args.add_phone[0], args.add_phone[1])
    if args.no_answer:
        return cmd_no_answer(args.no_answer, args.days)
    if args.declined:
        return cmd_declined(args.declined, args.notes)
    if args.connected:
        return cmd_connected(args.connected, args.notes)
    if args.export:
        return cmd_export()
    if args.stats:
        return cmd_stats()

    # Default: list due today
    return cmd_list(show_all=args.all)


if __name__ == "__main__":
    sys.exit(main())
