"""
send_followup_proposals.py  —  Follow-up on pending BCC proposals.

Sends from BOTH admin@ and ycao@ to each contact, with proposal PDF(s) attached.
Same-person contacts are merged into one email with all their proposals attached.

Usage:
    python send_followup_proposals.py              # Preview all (default)
    python send_followup_proposals.py --dry-run    # Show full email bodies
    python send_followup_proposals.py --send       # Send with Y confirmation
    python send_followup_proposals.py --send --only admin   # Only admin@
    python send_followup_proposals.py --send --only ycao    # Only ycao@
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import OrderedDict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from email_sender import (
    send_from_admin_with_attachment, send_from_admin_with_attachments,
    send_from_ycao_with_attachment, send_from_ycao_with_attachments,
)

PROJECTS = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")


# ── Follow-up email body ─────────────────────────────────────────────────────
def _body_single(first_name: str, project: str) -> str:
    return (
        f"Hi {first_name},\n\n"
        f"Just following up on the Third-Party Inspection proposal we sent over "
        f"for the {project} project. Wanted to make sure it reached you \u2014 "
        f"attaching it again here for easy reference.\n\n"
        f"As a quick reminder \u2014 billing is based on actual visits completed. "
        f"Our fee is a flat rate per inspection visit actually performed, and "
        f"you are never billed based on an upfront estimate. If the project "
        f"wraps up in fewer visits than anticipated, you only pay for what was "
        f"actually done.\n\n"
        f"We also offer same-day or next-business-day inspection scheduling "
        f"to help keep your project on track.\n\n"
        f"Also, as a quick note \u2014 BCC also offers Third-Party Plan Review "
        f"Services. If your team ever needs expedited code review or plan "
        f"review, we would be happy to assist.\n\n"
        f"Feel free to reach out if you have any questions or would like to "
        f"set up a brief call. Looking forward to hearing from you."
    )


def _body_multi(first_name: str, projects: list[str]) -> str:
    bullet_list = "\n".join(f"\u2022 {p}" for p in projects)
    return (
        f"Hi {first_name},\n\n"
        f"Just following up on the Third-Party Inspection proposals we sent over "
        f"for your current projects:\n\n"
        f"{bullet_list}\n\n"
        f"Wanted to make sure they reached you \u2014 attaching both proposals "
        f"again here for easy reference.\n\n"
        f"As a quick reminder \u2014 billing is based on actual visits completed. "
        f"Our fee is a flat rate per inspection visit actually performed, and "
        f"you are never billed based on an upfront estimate. If a project "
        f"wraps up in fewer visits than anticipated, you only pay for what was "
        f"actually done.\n\n"
        f"We also offer same-day or next-business-day inspection scheduling "
        f"to help keep your projects on track.\n\n"
        f"Also, as a quick note \u2014 BCC also offers Third-Party Plan Review "
        f"Services. If your team ever needs expedited code review or plan "
        f"review, we would be happy to assist.\n\n"
        f"Feel free to reach out if you have any questions or would like to "
        f"set up a brief call. Looking forward to hearing from you."
    )


def _subject_single(project_short: str) -> str:
    return f"Following Up \u2014 Inspection Proposal for {project_short} | Building Code Consulting LLC"


def _subject_multi(projects: list[str]) -> str:
    short = " & ".join(p.split("(")[0].strip() for p in projects)
    return f"Following Up \u2014 Inspection Proposals for {short} | Building Code Consulting LLC"


# ── Encoding-safe St. Joseph's PDF finder ─────────────────────────────────────
def _find_stjosephs_pdf() -> str:
    base = PROJECTS / "Keller Brothers"
    if not base.is_dir():
        return str(base / "NOT_FOUND.pdf")
    for folder in base.iterdir():
        if folder.is_dir() and "joseph" in folder.name.lower():
            pdfs = sorted(folder.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
            if pdfs:
                return str(pdfs[0])
    return str(base / "NOT_FOUND.pdf")


# ── Raw project entries (before grouping) ─────────────────────────────────────
RAW_ENTRIES = [
    # 1. Insomnia Cookies
    {
        "project": "Insomnia Cookies (701 Monroe St NE)",
        "contact": "Matt Burich",
        "first": "Matt",
        "email": "matt@builtwithbenchmark.com",
        "pdf": str(PROJECTS / "Built With Benchmark - Matt Burich" / "Insomnia Cookies"
                   / "Insomnia Cookies - 701 Monroe ST NE Code Compliance Inspection Proposal.pdf"),
    },
    # 2. Diner Bar / JW Marriott
    {
        "project": "Diner Bar at JW Marriott (1331 Pennsylvania Ave NW)",
        "contact": "Michael Cecchini",
        "first": "Michael",
        "email": "michael.cecchini@whiting-turner.com",
        "pdf": str(PROJECTS / "Whiting Turner - MD-Towson(HQ)"
                   / "JW Marriott - Restaurant and Diner Bar Third Party Code Inspection Proposal from Building Code Consulting -rebid.pdf"),
    },
    # 3. House Bar / 300 Morse St
    {
        "project": "House Bar (300 Morse St NE)",
        "contact": "Paul White",
        "first": "Paul",
        "email": "PWhite@infinitybuildinginc.com",
        "pdf": str(PROJECTS / "Infinity Building Services Inc"
                   / "House Bar - 300 Morse ST NE Washington DC - Third Party Code Inspection Proposal from BCC.pdf"),
    },
    # 4. Joe & The Juice
    {
        "project": "Joe & The Juice Union Station (50 Massachusetts Ave NE)",
        "contact": "Matt Burich",
        "first": "Matt",
        "email": "matt@builtwithbenchmark.com",
        "pdf": str(PROJECTS / "Built With Benchmark - Matt Burich" / "Joe & Juice Union Station"
                   / "Joe & The Juice Union Station - Third Party Code Inspection Proposal from BCC.pdf"),
    },
    # 5. Rivian
    {
        "project": "Rivian Flagship Renovation (1100 New York Ave NW)",
        "contact": "Bradley Miller",
        "first": "Bradley",
        "email": "bmiller@sachse.net",
        "pdf": str(PROJECTS / "Rivian Flagship Shop Reno- 1100 NY AVE NW"
                   / "RIVIAN Flagship Renovation - Third Party Code Inspection Proposal from BCC.pdf"),
    },
    # 7. St. Joseph's — SKIPPED (per Kyle, send later)
    # 7b. Alex Pauley — SKIPPED
    # 8. 3050 K St NW / Winmar
    {
        "project": "3050 K St NW 3rd & 4th Floors (Demo/White Box)",
        "contact": "Timothy Plum",
        "first": "Timothy",
        "email": "tplum@winmarconstruction.com",
        "pdf": str(PROJECTS / "Winmar Inc"
                   / "3050K St NW 3rd & 4th Floors Demo _ White Box TPI Proposal for Winmar Inc.pdf"),
    },
    # 9. Kolmac Expansion
    {
        "project": "Kolmac Expansion (1025 Vermont Ave NW)",
        "contact": "Jenny Lauer",
        "first": "Jenny",
        "email": "jlauer@hbwconstruction.com",
        "pdf": str(PROJECTS / "HBW Construction"
                   / "Kolmac Expansion 1025 Vermont Ave NW Code Inspection Proposal from Building Code Consulting.pdf"),
    },
    # 10. 20 F Street NW — SKIPPED (per Kyle, send later)
]


def _group_by_contact(entries: list[dict]) -> list[dict]:
    """Merge entries with the same email into one send with multiple attachments."""
    groups: OrderedDict[str, dict] = OrderedDict()
    for e in entries:
        key = e["email"].lower()
        if key not in groups:
            groups[key] = {
                "contact": e["contact"],
                "first": e["first"],
                "email": e["email"],
                "projects": [e["project"]],
                "pdfs": [e["pdf"]],
            }
        else:
            groups[key]["projects"].append(e["project"])
            if e["pdf"] not in groups[key]["pdfs"]:
                groups[key]["pdfs"].append(e["pdf"])
    return list(groups.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="Follow-up proposal emails (dual-account)")
    ap.add_argument("--send", action="store_true", help="Actually send (default: preview)")
    ap.add_argument("--dry-run", action="store_true", help="Show full email bodies")
    ap.add_argument("--only", choices=["admin", "ycao"], default=None,
                    help="Send from only one account")
    ap.add_argument("--yes", "-y", action="store_true",
                    help="Skip confirmation prompt")
    ap.add_argument("--delay", type=int, default=3,
                    help="Seconds between emails (default: 3)")
    args = ap.parse_args()

    # Resolve St. Joseph's PDF at runtime
    stj_pdf = _find_stjosephs_pdf()
    for e in RAW_ENTRIES:
        if e["pdf"] == "__STJOSEPHS__":
            e["pdf"] = stj_pdf

    # Group by contact email
    sends = _group_by_contact(RAW_ENTRIES)

    # ── Header ────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("BCC Proposal Follow-Up Sender (Dual Account)")
    print("=" * 70)
    print()

    # ── Verify all PDFs exist ─────────────────────────────────────────────────
    missing = []
    for s in sends:
        for pdf in s["pdfs"]:
            if not os.path.isfile(pdf):
                missing.append(f"  {s['contact']} \u2014 {pdf}")

    if missing:
        print("ERROR: Missing PDF files:\n")
        for m in missing:
            print(m)
        print("\nFix paths above and try again.")
        return 1

    # ── Determine accounts ────────────────────────────────────────────────────
    accounts: list[tuple[str, bool]] = []
    if args.only != "ycao":
        accounts.append(("admin@", False))
    if args.only != "admin":
        accounts.append(("ycao@", True))

    total_emails = len(sends) * len(accounts)

    print(f"  Unique contacts:  {len(sends)}")
    print(f"  Accounts:         {', '.join(a[0] for a in accounts)}")
    print(f"  Total emails:     {total_emails}")
    print(f"  St. Joseph's PDF: {os.path.basename(stj_pdf)}")
    print()

    # ── Preview ───────────────────────────────────────────────────────────────
    for i, s in enumerate(sends, 1):
        n_proj = len(s["projects"])
        is_multi = n_proj > 1
        if is_multi:
            subject = _subject_multi(s["projects"])
            body = _body_multi(s["first"], s["projects"])
        else:
            subject = _subject_single(s["projects"][0])
            body = _body_single(s["first"], s["projects"][0])

        print(f"  {i:>2}. {s['contact']:<22} <{s['email']}>")
        for p in s["projects"]:
            print(f"      Project: {p}")
        for pdf in s["pdfs"]:
            pdf_name = os.path.basename(pdf)
            print(f"      PDF: {pdf_name[:65]}{'...' if len(pdf_name) > 65 else ''}")
        if args.dry_run:
            print(f"      Subject: {subject}")
            print(f"\n{body}\n")
            print(f"      {'~' * 50}")
        print()

    if args.dry_run:
        print("[Dry run] No emails sent.")
        return 0

    if not args.send:
        print(f"Run with --send to send {total_emails} follow-up emails.")
        print(f"  python send_followup_proposals.py --send")
        print(f"  python send_followup_proposals.py --send --only admin")
        return 0

    # ── Confirm ───────────────────────────────────────────────────────────────
    if not args.yes:
        confirm = input(
            f"\nSend {total_emails} follow-up emails "
            f"({', '.join(a[0] for a in accounts)})? Type Y to confirm: "
        ).strip()
        if confirm.upper() != "Y":
            print("Aborted.")
            return 0

    # ── Send ──────────────────────────────────────────────────────────────────
    print(f"\nSending {total_emails} emails ({args.delay}s delay between each)...\n")
    sent = 0
    failed = 0

    for s in sends:
        is_multi = len(s["projects"]) > 1
        if is_multi:
            subject = _subject_multi(s["projects"])
            body = _body_multi(s["first"], s["projects"])
        else:
            subject = _subject_single(s["projects"][0])
            body = _body_single(s["first"], s["projects"][0])

        for label, use_ycao in accounts:
            if len(s["pdfs"]) == 1:
                # Single attachment — use original function
                if use_ycao:
                    ok, msg = send_from_ycao_with_attachment(
                        s["email"], subject, body, s["pdfs"][0])
                else:
                    ok, msg = send_from_admin_with_attachment(
                        s["email"], subject, body, s["pdfs"][0])
            else:
                # Multiple attachments
                if use_ycao:
                    ok, msg = send_from_ycao_with_attachments(
                        s["email"], subject, body, s["pdfs"])
                else:
                    ok, msg = send_from_admin_with_attachments(
                        s["email"], subject, body, s["pdfs"])

            proj_label = " + ".join(p.split("(")[0].strip() for p in s["projects"])
            if ok:
                print(f"  OK  [{label:<7}] {s['contact']:<22} ({proj_label})")
                sent += 1
            else:
                print(f"  FAIL[{label:<7}] {s['contact']:<22} \u2014 {msg}")
                failed += 1

            if args.delay > 0:
                time.sleep(args.delay)

    print(f"\nDone. Sent: {sent} | Failed: {failed} | Total: {total_emails}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    # Cross-machine lock only on real sends; previews and dry-runs run unwrapped.
    if "--send" in sys.argv and "--dry-run" not in sys.argv:
        from core_tools.active_operator import operator_lock
        with operator_lock("send_followup_proposals.py"):
            sys.exit(main())
    else:
        sys.exit(main())
