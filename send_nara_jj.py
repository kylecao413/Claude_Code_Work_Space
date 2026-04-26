"""Send NARA (PWC) + Interior Renovations (J&J) proposals. GUARDED."""
import sys
from pathlib import Path
from email_sender import send_from_admin_with_attachment

BASE = Path(__file__).resolve().parent
PROJECTS = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")
MARKER = BASE / ".send_nara_jj_20260423.marker"

EMAILS = [
    {
        "label": "NARA (PWC)",
        "to": "nerdelyi@pwccompanies.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – GPO NARA 4th Floor Renovation (732 N Capitol St NW)",
        "attachment": PROJECTS / "PWC Companies" / "GPO NARA 4th Floor Renovation" / "GPO NARA 4th Floor Renovation - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Nicole,

Thank you for the opportunity to bid on the GPO NARA 4th Floor Renovation at 732 North Capitol Street NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: full 5-discipline (Building, Mechanical, Electrical, Plumbing, Fire Protection) Third-Party Code Compliance Inspection. Aggressive flat rate of $325 per inspection visit on this 46,750 SF / 18-month scope.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. Given the extended duration and multi-phase nature of this project, actual visit count will adjust to the contractor's pour/close-in/energization milestones. Items such as sprinkler hydro/flush test, fire alarm and fire suppression acceptance testing, and exterior wall sheathing are included in the applicable visit if required by code for this scope.

We offer same-day or next-business-day inspection scheduling, including evenings and weekends at the same rate with no surcharge.

Happy to discuss any questions on the proposal or phasing.
""",
    },
    {
        "label": "J&J Interior Renovations",
        "to": "ibarry@jandjconst.net",
        "subject": "Third-Party Code Compliance Inspection Proposal – Interior Renovations (Multi-Floor), 717 Madison Place NW",
        "attachment": PROJECTS / "J&J 2000, Inc. DBA J&J Construction" / "Interior Renovations (Multi-Floor)" / "Interior Renovations (Multi-Floor) - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Ian,

Thank you for including BCC on the Interior Renovations (Multi-Floor) project at 717 Madison Place NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: given the light scope (corridor carpet, painting, lighting installation, marble replacement; no structural or extensive MEP work) our estimate is 2 inspection visits — one rough-in for lighting and one combo final — at the flat rate of $350 per visit.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The 2-visit count is our best estimate only — if additional visits are needed due to phasing or expanded scope, each is billed individually at the same rate. Never billed upfront, never capped by the estimate.

We offer same-day or next-business-day inspection scheduling, including evenings and weekends at the same rate with no surcharge.

Happy to answer any questions.
""",
    },
]


def main():
    if "--dry-run" in sys.argv:
        for em in EMAILS:
            print(f"\n=== {em['label']} ===\nTo: {em['to']}\nSubject: {em['subject']}\nBody:\n{em['body']}")
        print("[DRY RUN]")
        return
    if MARKER.exists():
        print(f"[GUARD] already sent (marker {MARKER.name}). Refusing re-send.")
        sys.exit(1)
    for em in EMAILS:
        if not em["attachment"].exists():
            print(f"[FAIL] attachment missing: {em['attachment']}")
            continue
        ok, msg = send_from_admin_with_attachment(
            to_email=em["to"], subject=em["subject"],
            body_plain=em["body"], attachment_path=str(em["attachment"]),
        )
        print(f"{'SENT' if ok else 'FAIL'} → {em['to']}: {msg}")
    MARKER.write_text("sent 2026-04-23")
    print(f"[marker: {MARKER.name}]")


if __name__ == "__main__":
    main()
