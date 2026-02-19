"""
reply_monitor.py — IMAP reply detection daemon.

Checks ycao@buildingcodeconsulting.com inbox via IMAP, matches incoming replies
against sent_log.csv, auto-marks replied=1, and sends a Telegram notification.

Requires in .env:
  PRIV_MAIL1_USER   — IMAP login (same as SMTP)
  PRIV_MAIL1_PASS   — IMAP password (same as SMTP)
  PRIV_MAIL1_IMAP   — IMAP host (default: mail.privateemail.com)

Usage:
    python reply_monitor.py              # Run once (check + notify)
    python reply_monitor.py --daemon     # Loop every 30 minutes
    python reply_monitor.py --interval 60  # Loop every 60 minutes
    python reply_monitor.py --days 14    # Look back 14 days (default: 7)
    python reply_monitor.py --dry-run    # Show matches without updating sent_log
"""
from __future__ import annotations

import argparse
import csv
import email as _email_lib
import imaplib
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
SENT_LOG = BASE_DIR / "sent_log.csv"

IMAP_HOST = os.environ.get("PRIV_MAIL1_IMAP", "mail.privateemail.com").strip().strip('"')
IMAP_USER = os.environ.get("PRIV_MAIL1_USER", "").strip().strip('"')
IMAP_PASS = os.environ.get("PRIV_MAIL1_PASS", "").strip().strip('"')
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
CHAT_IDS_RAW = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
CHAT_ID = CHAT_IDS_RAW.split(",")[0].strip() if CHAT_IDS_RAW else ""

FIELDNAMES = ["contact_email", "contact_name", "company", "project", "subject",
              "sent_at", "replied", "followup_sent_at"]


# ── Telegram notify ────────────────────────────────────────────────────────────
def _tg_notify(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        import requests as _req
        _req.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=10,
        )
    except Exception:
        pass


# ── sent_log helpers ──────────────────────────────────────────────────────────
def _load_log() -> list[dict]:
    if not SENT_LOG.exists():
        return []
    rows = []
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row.setdefault("replied", "")
            row.setdefault("followup_sent_at", "")
            rows.append(dict(row))
    return rows


def _save_log(rows: list[dict]) -> None:
    with open(SENT_LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


# ── IMAP fetch ────────────────────────────────────────────────────────────────
def _fetch_inbox_emails(days: int = 7) -> list[dict]:
    """
    Connect to IMAP and return list of {from_addr, subject, date} for recent emails.
    Checks INBOX only.
    """
    if not IMAP_USER or not IMAP_PASS:
        print("ERROR: PRIV_MAIL1_USER / PRIV_MAIL1_PASS not set in .env")
        return []

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    results = []

    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, 993) as imap:
            imap.login(IMAP_USER, IMAP_PASS)
            imap.select("INBOX")

            # Search for emails since cutoff
            status, data = imap.search(None, f'SINCE "{since_date}"')
            if status != "OK" or not data[0]:
                return []

            msg_ids = data[0].split()
            print(f"  IMAP: {len(msg_ids)} message(s) in INBOX since {since_date}")

            for msg_id in msg_ids:
                try:
                    status2, msg_data = imap.fetch(msg_id, "(RFC822.HEADER)")
                    if status2 != "OK":
                        continue
                    raw = msg_data[0][1] if msg_data and msg_data[0] else b""
                    msg = _email_lib.message_from_bytes(raw)
                    from_raw = msg.get("From", "")
                    subject_raw = msg.get("Subject", "")

                    # Decode encoded headers
                    from_decoded = _decode_header(from_raw)
                    subj_decoded = _decode_header(subject_raw)

                    # Extract email address from "Name <email>" format
                    from_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", from_decoded)
                    from_addr = from_match.group(0).lower() if from_match else from_decoded.lower()

                    results.append({
                        "from_addr": from_addr,
                        "subject": subj_decoded,
                        "raw_from": from_decoded,
                    })
                except Exception as e:
                    print(f"  Warning: could not parse message {msg_id}: {e}")
                    continue

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
        return []
    except Exception as e:
        print(f"Connection error: {e}")
        return []

    return results


def _decode_header(raw: str) -> str:
    """Decode RFC2047-encoded email header."""
    try:
        parts = _email_lib.header.decode_header(raw)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)
    except Exception:
        return raw


# ── Match logic ───────────────────────────────────────────────────────────────
def _strip_re(subject: str) -> str:
    """Remove 'Re:', 'Fwd:', 'Re[2]:' etc. prefixes."""
    return re.sub(r"^(re|fwd|fw)(\[\d+\])?:\s*", "", subject.strip(), flags=re.IGNORECASE).strip()


def find_matches(inbox_emails: list[dict], log_rows: list[dict]) -> list[tuple[dict, dict]]:
    """
    Match inbox replies against sent_log rows.
    A match requires: from_addr == contact_email AND stripped subjects match.
    Returns list of (inbox_email, log_row) pairs for new replies.
    """
    matches = []
    already_replied = {
        row["contact_email"].lower()
        for row in log_rows
        if row.get("replied", "").strip() in ("1", "true", "yes")
    }

    for inbox_email in inbox_emails:
        sender = inbox_email["from_addr"].lower()
        inbox_subj = _strip_re(inbox_email["subject"]).lower()

        for row in log_rows:
            row_email = row.get("contact_email", "").lower()
            if sender != row_email:
                continue
            if row_email in already_replied:
                continue
            # Subject match: inbox subject should contain core part of original subject
            sent_subj = _strip_re(row.get("subject", "")).lower()
            # Fuzzy match: check if key words from sent subject appear in inbox subject
            if sent_subj and (sent_subj in inbox_subj or inbox_subj in sent_subj):
                matches.append((inbox_email, row))
                break
            # Also match purely on email (no subject required — sometimes replies diverge)
            # Only do this if sender is in sent_log and not already flagged
            # Conservative: require at least 30% word overlap
            sent_words = set(sent_subj.split())
            inbox_words = set(inbox_subj.split())
            if sent_words and len(sent_words & inbox_words) / len(sent_words) >= 0.3:
                matches.append((inbox_email, row))
                break

    return matches


# ── Main logic ────────────────────────────────────────────────────────────────
def run_once(days: int = 7, dry_run: bool = False) -> int:
    print(f"\n{'='*50}")
    print(f"Reply Monitor — checking inbox ({days} days back)")
    print(f"{'='*50}")

    rows = _load_log()
    if not rows:
        print("sent_log.csv is empty — nothing to match against.")
        return 0

    unreplied = [r for r in rows if not r.get("replied", "").strip()]
    print(f"Sent log: {len(rows)} total, {len(unreplied)} awaiting reply")

    inbox_emails = _fetch_inbox_emails(days=days)
    if not inbox_emails:
        print("No inbox emails found (or IMAP error).")
        return 0

    matches = find_matches(inbox_emails, rows)
    if not matches:
        print("No new replies detected.")
        return 0

    print(f"\n🎉 {len(matches)} reply match(es) found:")
    for inbox_email, row in matches:
        print(f"  {row.get('contact_name', '?')} <{row['contact_email']}> — {row.get('company', '?')}")
        print(f"    Subject: {inbox_email['subject'][:80]}")

    if dry_run:
        print("\n[dry-run] Not updating sent_log.")
        return 0

    # Update sent_log
    reply_emails = {row["contact_email"].lower() for _, row in matches}
    updated = 0
    for row in rows:
        if row.get("contact_email", "").lower() in reply_emails:
            row["replied"] = "1"
            updated += 1

    _save_log(rows)
    print(f"\nUpdated {updated} row(s) in sent_log.csv — replied=1")

    # Telegram notification
    notif_lines = [f"📩 {len(matches)} reply detected by BCC bot:\n"]
    for inbox_email, row in matches:
        notif_lines.append(
            f"• {row.get('contact_name', '?')} ({row.get('company', '?')}) replied!\n"
            f"  Re: {inbox_email['subject'][:60]}"
        )
    notif_lines.append("\n✅ sent_log.csv updated. Follow-ups suppressed for these contacts.")
    _tg_notify("\n".join(notif_lines))
    print("Telegram notification sent.")
    return len(matches)


def main() -> int:
    ap = argparse.ArgumentParser(description="IMAP reply monitor for BCC cold outreach")
    ap.add_argument("--daemon",   action="store_true", help="Run continuously (loop)")
    ap.add_argument("--interval", type=int, default=30, help="Daemon loop interval in minutes (default: 30)")
    ap.add_argument("--days",     type=int, default=7,  help="Days of inbox to scan (default: 7)")
    ap.add_argument("--dry-run",  action="store_true",  help="Show matches without updating sent_log")
    args = ap.parse_args()

    if args.daemon:
        print(f"Reply monitor daemon started — checking every {args.interval} minutes.")
        print("Press Ctrl+C to stop.")
        while True:
            try:
                run_once(days=args.days, dry_run=args.dry_run)
            except KeyboardInterrupt:
                print("\nStopped.")
                return 0
            except Exception as e:
                print(f"Error in daemon loop: {e}")
            print(f"\nSleeping {args.interval} minutes...")
            time.sleep(args.interval * 60)
    else:
        run_once(days=args.days, dry_run=args.dry_run)
        return 0


if __name__ == "__main__":
    sys.exit(main())
