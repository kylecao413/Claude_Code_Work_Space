"""
daily_sender.py — Rate-limited daily email sender (dual-account, 40/day).

Sends up to 40 CW cold outreach emails per day:
  - First 20 from admin@buildingcodeconsulting.com
  - Next 20 from ycao@buildingcodeconsulting.com

Prioritized by lead score (from DC_Top100_*.md if present).
Tracks sends in sent_log.csv. Won't re-send to anyone already in the log.

Usage:
    python daily_sender.py                             # Preview: show who would be sent today
    python daily_sender.py --send                      # Send up to 40 emails (requires confirmation)
    python daily_sender.py --limit 20                  # Override daily cap
    python daily_sender.py --sender admin              # Only use admin@ (20 max)
    python daily_sender.py --sender ycao               # Only use ycao@ (20 max)
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

from email_sender import (
    send_from_admin, send_from_admin_with_attachment,
    send_from_ycao, send_from_ycao_with_attachment,
)

BASE_DIR     = Path(__file__).resolve().parent
OUTBOUND_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
SENT_LOG     = BASE_DIR / "sent_log.csv"

# 20 per account × 2 accounts = 40 total
PER_ACCOUNT_LIMIT   = 20
DEFAULT_DAILY_LIMIT = PER_ACCOUNT_LIMIT * 2   # 40


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


def _count_sent_today() -> dict[str, int]:
    """Count emails sent today (UTC) per sender. Returns {'admin': N, 'ycao': N, 'total': N}."""
    counts = {"admin": 0, "ycao": 0, "total": 0}
    if not SENT_LOG.exists():
        return counts
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = row.get("sent_at", "") or row.get("followup_sent_at", "")
            if ts and ts[:10] == today:
                sender = row.get("sent_from", "admin")
                key = "ycao" if "ycao" in sender else "admin"
                counts[key] += 1
                counts["total"] += 1
    return counts


def _log_sent(em: dict, sent_from: str) -> None:
    """Append a send record to sent_log.csv."""
    write_header = not SENT_LOG.exists()
    fieldnames = ["contact_email", "contact_name", "company", "project", "subject",
                  "sent_at", "sent_from", "replied", "followup_sent_at"]
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
            "sent_from":      sent_from,
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


# ── Send helpers ──────────────────────────────────────────────────────────────
def _send_one(em: dict, use_ycao: bool, attachment_path: str) -> tuple[bool, str]:
    """Send a single email from the specified account."""
    if use_ycao:
        if attachment_path:
            return send_from_ycao_with_attachment(em["to_email"], em["subject"], em["body"], attachment_path)
        return send_from_ycao(em["to_email"], em["subject"], em["body"])
    else:
        if attachment_path:
            return send_from_admin_with_attachment(em["to_email"], em["subject"], em["body"], attachment_path)
        return send_from_admin(em["to_email"], em["subject"], em["body"])


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Rate-limited daily email sender (default: 40/day across 2 accounts)")
    ap.add_argument("--send",       action="store_true", help="Actually send emails (default: preview only)")
    ap.add_argument("--all",        action="store_true", help="Send all remaining drafts (ignore daily cap)")
    ap.add_argument("--dry-run",    action="store_true", help="Show full email bodies without sending")
    ap.add_argument("--limit",      type=int, default=DEFAULT_DAILY_LIMIT,
                                    help=f"Total daily email cap (default: {DEFAULT_DAILY_LIMIT})")
    ap.add_argument("--sender",     choices=["both", "admin", "ycao"], default="both",
                                    help="Which account(s) to send from (default: both)")
    ap.add_argument("--attachment", default="", help="Path to PDF to attach to all emails")
    ap.add_argument("--company",    default="", help="Filter: only send for matching company substring")
    args = ap.parse_args()

    # Determine per-account caps based on --sender
    if args.sender == "admin":
        admin_cap = args.limit if args.all else args.limit
        ycao_cap  = 0
    elif args.sender == "ycao":
        admin_cap = 0
        ycao_cap  = args.limit if args.all else args.limit
    else:  # both
        half = args.limit // 2
        admin_cap = half
        ycao_cap  = args.limit - half   # gets the extra 1 if limit is odd

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

    # Apply daily cap per account
    today_counts = _count_sent_today()
    if not args.all:
        admin_remaining = max(0, admin_cap - today_counts["admin"])
        ycao_remaining  = max(0, ycao_cap  - today_counts["ycao"])
    else:
        admin_remaining = len(emails)
        ycao_remaining  = len(emails)

    total_remaining = admin_remaining + ycao_remaining

    if total_remaining <= 0 and not args.all:
        print(f"Daily limit reached: sent {today_counts['total']} today "
              f"(admin: {today_counts['admin']}, ycao: {today_counts['ycao']}).")
        print("Use --all to override, or --limit to increase cap.")
        return 0

    # Assign senders: first N → admin@, next M → ycao@
    batch: list[tuple[dict, bool]] = []  # (email_dict, use_ycao)
    admin_assigned = 0
    ycao_assigned  = 0
    for em in emails:
        if admin_assigned < admin_remaining:
            batch.append((em, False))
            admin_assigned += 1
        elif ycao_assigned < ycao_remaining:
            batch.append((em, True))
            ycao_assigned += 1
        else:
            break

    print(f"\n{'='*65}")
    print(f"Daily Sender Status")
    print(f"{'='*65}")
    print(f"  Total CW drafts:             {len(drafts)}")
    print(f"  Already in sent_log:         {skipped}")
    print(f"  Remaining to send:           {len(emails)}")
    print(f"  Sent today — admin@:         {today_counts['admin']}/{admin_cap}")
    print(f"  Sent today — ycao@:          {today_counts['ycao']}/{ycao_cap}")
    print(f"  This batch:                  {len(batch)} "
          f"({admin_assigned} from admin@, {ycao_assigned} from ycao@)")
    if scores:
        print(f"  Ordered by Top-100 score (highest priority first)")
    print()

    if not batch:
        print("Nothing to send.")
        return 0

    # Show batch
    for i, (em, use_ycao) in enumerate(batch, 1):
        score = scores.get(em["to_email"].lower(), 0.0)
        score_str  = f" [score: {score}]" if score else ""
        sender_tag = "ycao@" if use_ycao else "admin@"
        print(f"  {i:>3}. [{sender_tag}] {em['contact_name']:<22} {em['company']:<28}{score_str}")
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
        f"\nSend {len(batch)} email(s) "
        f"({admin_assigned} from admin@, {ycao_assigned} from ycao@)? (Y to confirm): "
    ).strip()
    if confirm.upper() != "Y":
        print("Aborted.")
        return 0

    # Send
    print(f"\nSending {len(batch)} email(s)...")
    sent_count = 0
    for em, use_ycao in batch:
        ok, msg = _send_one(em, use_ycao, attachment_path)
        sender_label = "ycao@" if use_ycao else "admin@"
        sent_from    = "ycao@buildingcodeconsulting.com" if use_ycao else "admin@buildingcodeconsulting.com"
        if ok:
            print(f"  ✅ [{sender_label}] {em['contact_name']} <{em['to_email']}> ({em['company']})")
            _log_sent(em, sent_from)
            sent_count += 1
        else:
            print(f"  ❌ FAILED [{sender_label}]: {em['to_email']} — {msg}")

    total_today = today_counts["total"] + sent_count
    print(f"\nDone. Sent {sent_count}/{len(batch)} emails.")
    print(f"Total sent today: {total_today}/{args.limit}")
    if len(emails) - sent_count > 0 and not args.all:
        print(f"Remaining in queue: {len(emails) - sent_count} (run again tomorrow or use --all)")
    return 0 if sent_count == len(batch) else 1


if __name__ == "__main__":
    sys.exit(main())
