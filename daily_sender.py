"""
daily_sender.py — Rate-limited daily email sender.

Sends up to N (default 20) CW cold outreach emails per day, prioritized by
lead score (from DC_Top100_*.md if present), with PDF attachment support.

Tracks sends in sent_log.csv. Won't re-send to anyone already in the log.

Usage:
    python daily_sender.py                             # Preview: show who would be sent today
    python daily_sender.py --send                      # Send up to 20 emails (requires confirmation)
    python daily_sender.py --limit 10                  # Override daily cap
    python daily_sender.py --dry-run                   # Preview email bodies without sending
    python daily_sender.py --attachment "path/to.pdf"  # Attach PDF to all emails
    python daily_sender.py --send --all                # Send without daily cap (all remaining drafts)
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from email_sender import send_from_admin, send_from_admin_with_attachment

BASE_DIR    = Path(__file__).resolve().parent
OUTBOUND_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
SENT_LOG    = BASE_DIR / "sent_log.csv"

DEFAULT_DAILY_LIMIT = 20


# ── Sent log helpers ──────────────────────────────────────────────────────────
def _load_sent_emails() -> set[str]:
    """Return set of email addresses already in sent_log (lowercase)."""
    if not SENT_LOG.exists():
        return set()
    sent: set[str] = set()
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            e = row.get("contact_email", "").strip().lower()
            if e:
                sent.add(e)
    return sent


def _count_sent_today() -> int:
    """Count emails sent today (UTC) from sent_log."""
    if not SENT_LOG.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = row.get("sent_at", "") or row.get("followup_sent_at", "")
            if ts and ts[:10] == today:
                count += 1
    return count


def _log_sent(em: dict) -> None:
    """Append a send record to sent_log.csv."""
    write_header = not SENT_LOG.exists()
    fieldnames = ["contact_email", "contact_name", "company", "project", "subject",
                  "sent_at", "replied", "followup_sent_at"]
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow({
            "contact_email":  em.get("to_email", ""),
            "contact_name":   em.get("contact_name", ""),
            "company":        em.get("company", ""),
            "project":        em.get("project", ""),
            "subject":        em.get("subject", ""),
            "sent_at":        datetime.now(timezone.utc).isoformat(),
            "replied":        "",
            "followup_sent_at": "",
        })


# ── Draft parsing ─────────────────────────────────────────────────────────────
def _parse_draft(fpath: Path) -> dict | None:
    """Parse a CW_*.md draft file. Returns dict or None if invalid."""
    try:
        text = fpath.read_text(encoding="utf-8")
    except Exception:
        return None

    to_m      = re.search(r"\*\*TO:\*\*\s*(.+?)(?:\n|$)", text)
    subj_m    = re.search(r"\*\*SUBJECT:\*\*\s*(.+?)(?:\n|$)", text)
    project_m = re.search(r"\*\*PROJECT:\*\*\s*(.+?)(?:\n|$)", text)
    company_m = re.search(r"# CW Cold Outreach — (.+?)(?:\n|$)", text)

    if not to_m or not subj_m:
        return None

    to_raw = to_m.group(1).strip()
    email_m = re.search(r"<(.+?)>", to_raw)
    to_email = email_m.group(1).strip() if email_m else to_raw
    contact_name = to_raw.split("<")[0].strip() if "<" in to_raw else ""

    body_split = text.split("---\n\n", 1)
    body = body_split[1].strip() if len(body_split) > 1 else ""

    if not to_email or "@" not in to_email or not body:
        return None

    return {
        "to_email":     to_email,
        "contact_name": contact_name,
        "subject":      subj_m.group(1).strip(),
        "body":         body,
        "company":      (company_m.group(1).strip() if company_m else fpath.stem),
        "project":      (project_m.group(1).strip() if project_m else ""),
        "file":         fpath,
    }


# ── Top-100 score lookup ──────────────────────────────────────────────────────
def _load_top100_scores() -> dict[str, float]:
    """
    Parse the most recent DC_Top100_*.md to get score per email address.
    Returns {email_lower: score}. Used to sort outbound drafts by priority.
    """
    top100_files = sorted(BASE_DIR.glob("DC_Top100_*.md"), reverse=True)
    if not top100_files:
        return {}
    scores: dict[str, float] = {}
    try:
        text = top100_files[0].read_text(encoding="utf-8")
        for line in text.splitlines():
            # Table row: | N | Project | Stage | Focus | Value | Company | Role | Contact | Email | Score |
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 11:
                email_col = parts[9].strip().lower()
                score_col = parts[10].strip()
                if "@" in email_col:
                    try:
                        scores[email_col] = float(score_col)
                    except ValueError:
                        pass
    except Exception:
        pass
    return scores


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Rate-limited daily email sender (default: 20/day)")
    ap.add_argument("--send",       action="store_true", help="Actually send emails (default: preview only)")
    ap.add_argument("--all",        action="store_true", help="Send all remaining drafts (ignore daily cap)")
    ap.add_argument("--dry-run",    action="store_true", help="Show full email bodies without sending")
    ap.add_argument("--limit",      type=int, default=DEFAULT_DAILY_LIMIT,
                                    help=f"Daily email cap (default: {DEFAULT_DAILY_LIMIT})")
    ap.add_argument("--attachment", default="", help="Path to PDF to attach to all emails")
    ap.add_argument("--company",    default="", help="Filter: only send for matching company substring")
    args = ap.parse_args()

    # Load all drafts
    drafts = sorted(OUTBOUND_DIR.glob("CW_*.md"))
    if not drafts:
        print("No CW_*.md drafts found in Pending_Approval/Outbound/")
        print("Run first: python run_cw_leads_pipeline.py")
        return 1

    # Parse drafts
    emails = []
    for fpath in drafts:
        em = _parse_draft(fpath)
        if not em:
            continue
        if args.company and args.company.lower() not in em["company"].lower():
            continue
        emails.append(em)

    if not emails:
        print("No parseable drafts found.")
        return 1

    # Deduplicate against sent_log
    already_sent = _load_sent_emails()
    emails = [em for em in emails if em["to_email"].lower() not in already_sent]
    skipped = len(drafts) - len(emails)

    # Sort by Top-100 score (higher score first)
    scores = _load_top100_scores()
    emails.sort(key=lambda em: -scores.get(em["to_email"].lower(), 0.0))

    # Apply daily cap
    sent_today = _count_sent_today()
    remaining_cap = (args.limit - sent_today) if not args.all else len(emails)

    if remaining_cap <= 0 and not args.all:
        print(f"Daily limit reached: already sent {sent_today} today (cap: {args.limit}).")
        print(f"Use --all to override, or --limit to increase cap.")
        return 0

    batch = emails[:max(0, remaining_cap)]

    print(f"\n{'='*60}")
    print(f"Daily Sender Status")
    print(f"{'='*60}")
    print(f"  Total CW drafts:      {len(drafts)}")
    print(f"  Already in sent_log:  {skipped}")
    print(f"  Remaining to send:    {len(emails)}")
    print(f"  Sent today (so far):  {sent_today}")
    print(f"  Daily cap:            {args.limit} {'(overridden)' if args.all else ''}")
    print(f"  This batch:           {len(batch)}")
    if scores:
        print(f"  Ordered by Top-100 score (highest priority first)")
    print()

    if not batch:
        print("Nothing to send.")
        return 0

    # Show batch
    for i, em in enumerate(batch, 1):
        score = scores.get(em["to_email"].lower(), 0.0)
        score_str = f" [score: {score}]" if score else ""
        print(f"  {i:>3}. {em['contact_name']:<25} {em['company']:<30} {score_str}")
        if args.dry_run:
            print(f"       Subject: {em['subject']}")
            print(f"       Body preview: {em['body'][:120].strip()}...")
            print()

    if args.dry_run:
        print("[dry-run] No emails sent.")
        return 0

    if not args.send:
        print(f"\nRun with --send to send this batch of {len(batch)} email(s).")
        print(f"  python daily_sender.py --send")
        if args.attachment:
            print(f"  (attachment: {args.attachment})")
        return 0

    # Validate attachment
    attachment_path = args.attachment.strip()
    if attachment_path and not os.path.isfile(attachment_path):
        print(f"ERROR: Attachment not found: {attachment_path}")
        return 1

    # Confirm
    confirm = input(
        f"\nSend {len(batch)} email(s) from admin@buildingcodeconsulting.com? (Y to confirm): "
    ).strip()
    if confirm.upper() != "Y":
        print("Aborted.")
        return 0

    # Send
    print(f"\nSending {len(batch)} email(s)...")
    sent_count = 0
    for em in batch:
        if attachment_path:
            ok, msg = send_from_admin_with_attachment(
                em["to_email"], em["subject"], em["body"], attachment_path
            )
        else:
            ok, msg = send_from_admin(em["to_email"], em["subject"], em["body"])

        if ok:
            print(f"  ✅ {em['contact_name']} <{em['to_email']}> ({em['company']})")
            _log_sent(em)
            sent_count += 1
        else:
            print(f"  ❌ FAILED: {em['to_email']} — {msg}")

    print(f"\nDone. Sent {sent_count}/{len(batch)} emails.")
    print(f"Total sent today: {sent_today + sent_count}/{args.limit}")
    if len(emails) - sent_count > 0 and not args.all:
        print(f"Remaining in queue: {len(emails) - sent_count} (run again tomorrow or use --all)")
    return 0 if sent_count == len(batch) else 1


if __name__ == "__main__":
    sys.exit(main())
