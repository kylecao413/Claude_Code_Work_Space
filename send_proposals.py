"""
发送两封提案邮件（带 PDF 附件）。
运行前必须已获得用户明确审批（"Y" 或 "Proceed with sending"）。
用法: python send_proposals.py --project 20f  (或 stjosephs 或 both)
"""
import argparse
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from email_sender import send_from_admin_with_attachment

PROJECTS_BASE = r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects"

PROPOSALS = {
    "20f": {
        "to": "acolon@hbwconstruction.com",
        "contact": "Angel Colon",
        "subject": "Third-Party Code Compliance Inspection Proposal \u2014 20 F St NW Suite 550 | Building Code Consulting LLC",
        "pdf": os.path.join(
            PROJECTS_BASE,
            "HBW Construction",
            "20 F Street Northwest, Suite 550 Tenant Renovation",
            "20 F Street Northwest, Suite 550 Tenant Renovation - Third Party Code Inspection Proposal from BCC.pdf",
        ),
        "body": """\
Hi Angel,

Thank you for the opportunity to connect with HBW Construction. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC) for the 20 F Street Northwest, Suite 550 Tenant Renovation project.

A few quick highlights:

Billing is based on actual visits completed — our fee is a flat rate per inspection visit actually performed. You will never be billed based on an upfront estimate or a projected number of visits. If your project wraps up in fewer visits than anticipated, you only pay for what was actually done.

As a DC-licensed Third-Party Agency, BCC provides same-day or next-business-day inspection scheduling to keep your project on track.

Also, as a quick note — in addition to Third-Party Inspection services, Building Code Consulting LLC also offers Third-Party Plan Review Services. If your team ever needs expedited pre-submission code review, peer review, or plan review for DC or other jurisdictions, we're happy to help with that as well.

Please don't hesitate to reach out with any questions, or if you'd like to set up a brief call to walk through the proposal. We look forward to supporting the project.\
""",
    },
    "stjosephs": {
        "to": "apauley@kellerbrothers.com",
        "contact": "Alex Pauley",
        "subject": "Inspection Proposal for St. Joseph\u2019s on Capitol Hill Phase I \u2014 Building Code Consulting LLC",
        "pdf": os.path.join(
            PROJECTS_BASE,
            "Keller Brothers",
            "St. Joseph's on Capitol Hill \u2013 Phase I",
            "St. Joseph's on Capitol Hill \u2013 Phase I - Third Party Code Inspection Proposal from BCC - CORRECTED.pdf",
        ),
        "body": """\
Hi Alex,

Thank you for the opportunity to bid on the St. Joseph's on Capitol Hill \u2013 Phase I project. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

A few quick highlights:

Billing is based on actual visits completed \u2014 our fee is a flat rate per inspection visit actually performed. You are never billed based on the number of visits estimated in the proposal. If the project wraps up in fewer inspections than projected, you only pay for what was actually done.

As a DC-licensed Third-Party Agency, BCC provides same-day or next-business-day inspection scheduling to keep your critical milestones on track.

Also, as a quick heads-up \u2014 in addition to Third-Party Inspection services, Building Code Consulting LLC also offers Third-Party Plan Review Services. If Keller Brothers ever needs expedited pre-submission code review, peer review, or plan review support for DC or other jurisdictions, we'd love to assist there as well.

Please feel free to reach out with any questions, or if you'd like to hop on a quick call to discuss the proposal. We genuinely appreciate the consideration and look forward to working with the Keller Brothers team.\
""",
    },
}


def send_one(key: str, dry_run: bool = False) -> bool:
    p = PROPOSALS[key]
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Sending to {p['contact']} <{p['to']}>")
    print(f"  Subject : {p['subject']}")
    print(f"  PDF     : {os.path.basename(p['pdf'])}")
    if not os.path.isfile(p["pdf"]):
        print(f"  ERROR: PDF not found at {p['pdf']}")
        return False
    if dry_run:
        print("  [Dry run — not actually sent]")
        return True
    ok, msg = send_from_admin_with_attachment(
        to_email=p["to"],
        subject=p["subject"],
        body_plain=p["body"],
        attachment_path=p["pdf"],
    )
    if ok:
        print(f"  OK: {msg}")
    else:
        print(f"  FAILED: {msg}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Send BCC proposal emails with PDF attachments.")
    parser.add_argument("--project", choices=["20f", "stjosephs", "both"], default="both",
                        help="Which proposal to send (default: both)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent without actually sending")
    args = parser.parse_args()

    keys = ["20f", "stjosephs"] if args.project == "both" else [args.project]

    print("=" * 60)
    print("BCC Proposal Email Sender")
    print("=" * 60)

    all_ok = True
    for key in keys:
        ok = send_one(key, dry_run=args.dry_run)
        all_ok = all_ok and ok

    print("\n" + ("=" * 60))
    if all_ok:
        print("All emails sent successfully." if not args.dry_run else "Dry run complete.")
    else:
        print("One or more emails FAILED. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
