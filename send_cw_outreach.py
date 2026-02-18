"""
send_cw_outreach.py — Send approved CW cold outreach emails after Kyle's review.

Reads all CW_*.md drafts from Pending_Approval/Outbound/.
Parses TO:, SUBJECT:, BODY from each draft file.
Requires explicit confirmation before sending each email.

Usage:
    python send_cw_outreach.py                # interactive prompt per email
    python send_cw_outreach.py --all          # confirm all at once (still asks once)
    python send_cw_outreach.py --dry-run      # show what would be sent, no actual send
    python send_cw_outreach.py --company "Turner"  # filter by company name substring
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

BASE_DIR = Path(__file__).resolve().parent
OUTBOUND_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
SENT_LOG = BASE_DIR / "sent_log.csv"


def _parse_draft(fpath: Path) -> dict | None:
    """
    Parse a CW_*.md draft file.
    Extracts: to_email, contact_name, subject, body, company, project.
    Returns None if file can't be parsed as a valid email draft.
    """
    try:
        text = fpath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Could not read {fpath.name}: {e}")
        return None

    # Required fields
    to_match = re.search(r"\*\*TO:\*\*\s*(.+?)(?:\n|$)", text)
    subj_match = re.search(r"\*\*SUBJECT:\*\*\s*(.+?)(?:\n|$)", text)
    project_match = re.search(r"\*\*PROJECT:\*\*\s*(.+?)(?:\n|$)", text)
    company_match = re.search(r"# CW Cold Outreach — (.+?)(?:\n|$)", text)
    phone_match = re.search(r"\*\*PHONE:\*\*\s*(.+?)(?:\n|$)", text)

    if not to_match or not subj_match:
        return None

    # Parse name and email from "Contact Name <email@domain.com>"
    to_raw = to_match.group(1).strip()
    email_in_brackets = re.search(r"<(.+?)>", to_raw)
    to_email = email_in_brackets.group(1).strip() if email_in_brackets else to_raw
    contact_name = to_raw.split("<")[0].strip() if "<" in to_raw else ""

    subject = subj_match.group(1).strip()
    project = (project_match.group(1).strip() if project_match else "").strip()
    company = (company_match.group(1).strip() if company_match else fpath.stem).strip()
    phone = (phone_match.group(1).strip() if phone_match else "").strip()
    phone = "" if phone == "—" else phone

    # Extract body: everything after "---\n\n"
    body_split = text.split("---\n\n", 1)
    body = body_split[1].strip() if len(body_split) > 1 else ""

    if not to_email or "@" not in to_email or not body:
        return None

    return {
        "to_email": to_email,
        "contact_name": contact_name,
        "subject": subject,
        "body": body,
        "company": company,
        "project": project,
        "phone": phone,
        "file": fpath,
    }


def _log_sent(em: dict) -> None:
    """Append send record to sent_log.csv."""
    write_header = not SENT_LOG.exists()
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["contact_email", "contact_name", "company", "project", "subject", "sent_at"])
        w.writerow([
            em["to_email"],
            em["contact_name"],
            em["company"],
            em["project"],
            em["subject"],
            datetime.now(timezone.utc).isoformat(),
        ])


def main() -> int:
    ap = argparse.ArgumentParser(description="Send approved CW cold outreach emails")
    ap.add_argument("--all", action="store_true", help="Confirm all drafts at once (single Y/N prompt)")
    ap.add_argument("--dry-run", action="store_true", help="Print emails without actually sending")
    ap.add_argument("--company", default="", help="Filter: only send for companies matching this substring")
    ap.add_argument("--files", default="", help="Filter: comma-separated filename substrings (e.g. 'Michelle_Wilson,Peter_Otteni')")
    ap.add_argument("--attachment", default="", help="Path to PDF file to attach to all outgoing emails")
    args = ap.parse_args()

    drafts = sorted(OUTBOUND_DIR.glob("CW_*.md"))
    if not drafts:
        print("No CW_*.md drafts found in Pending_Approval/Outbound/")
        print("Run first: python run_cw_leads_pipeline.py")
        return 1

    # Parse all drafts
    emails = []
    for fpath in drafts:
        em = _parse_draft(fpath)
        if not em:
            print(f"  Skipping unparseable draft: {fpath.name}")
            continue
        if args.company and args.company.lower() not in em["company"].lower():
            continue
        if args.files:
            substrings = [s.strip() for s in args.files.split(",") if s.strip()]
            if not any(s.lower() in fpath.name.lower() for s in substrings):
                continue
        emails.append(em)

    if not emails:
        print(f"No matching drafts found{' for company: ' + args.company if args.company else ''}.")
        return 1

    print(f"\n{'='*60}")
    print(f"CW Cold Outreach Sender — {len(emails)} email(s) to review")
    print(f"{'='*60}\n")

    for i, em in enumerate(emails, 1):
        print(f"[{i}/{len(emails)}]")
        print(f"  TO:      {em['contact_name']} <{em['to_email']}>")
        if em["phone"]:
            print(f"  PHONE:   {em['phone']}")
        print(f"  PROJECT: {em['project']}")
        print(f"  COMPANY: {em['company']}")
        print(f"  SUBJECT: {em['subject']}")
        print(f"  BODY:\n")
        for line in em["body"].split("\n"):
            print(f"    {line}")
        print()

    if args.dry_run:
        print("[Dry run] No emails sent.")
        return 0

    if args.all:
        # Single confirmation for all
        confirm = input(f"\nSend ALL {len(emails)} email(s) from admin@buildingcodeconsulting.com? (Y to confirm): ").strip()
        if confirm.upper() != "Y":
            print("Aborted.")
            return 0
        to_send = emails
    else:
        # Per-email confirmation
        to_send = []
        for em in emails:
            confirm = input(
                f"\nSend to {em['contact_name']} <{em['to_email']}> for {em['company']}? (Y/n/q): "
            ).strip()
            if confirm.upper() == "Q":
                print("Quitting.")
                break
            if confirm.upper() == "Y":
                to_send.append(em)
            else:
                print(f"  Skipped: {em['to_email']}")

    if not to_send:
        print("No emails selected for sending.")
        return 0

    attachment_path = args.attachment.strip() if args.attachment else ""
    if attachment_path:
        if not Path(attachment_path).is_file():
            print(f"ERROR: Attachment not found: {attachment_path}")
            return 1
        print(f"Attachment: {attachment_path}")

    print(f"\nSending {len(to_send)} email(s)...")
    sent_count = 0
    for em in to_send:
        if attachment_path:
            ok, msg = send_from_admin_with_attachment(em["to_email"], em["subject"], em["body"], attachment_path)
        else:
            ok, msg = send_from_admin(em["to_email"], em["subject"], em["body"])
        if ok:
            print(f"  OK: {em['to_email']} ({em['company']})")
            _log_sent(em)
            sent_count += 1
        else:
            print(f"  FAILED: {em['to_email']} — {msg}")

    print(f"\nDone. Sent {sent_count}/{len(to_send)} emails.")
    if sent_count > 0:
        print(f"Send log: {SENT_LOG}")
    return 0 if sent_count == len(to_send) else 1


if __name__ == "__main__":
    sys.exit(main())
