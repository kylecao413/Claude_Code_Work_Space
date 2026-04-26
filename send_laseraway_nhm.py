"""
Send LaserAway + NHM proposal emails (admin@, CC ycao@, PDF attached).
GUARDED: refuses to re-run if marker file exists.
"""
import sys
from pathlib import Path
from email_sender import send_from_admin_with_attachment

BASE = Path(__file__).resolve().parent
PROJECTS = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")
MARKER = BASE / ".send_laseraway_nhm_20260422.marker"

EMAILS = [
    {
        "label": "LaserAway",
        "to": "sandrar@horizonretail.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – LaserAway, 1427 P Street NW (Washington DC)",
        "attachment": PROJECTS / "Horizon Retail Construction" / "LaserAway Washington, DC" / "LaserAway Washington, DC - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Sandra,

Thank you for the opportunity to bid on the LaserAway fit-out at 1427 P Street NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: flat rate of $350 per inspection visit across Building, Mechanical, Electrical, Plumbing, and Fire Protection for the DC Third-Party Inspection program.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. Additional items (sprinkler hydro/flush test, fire alarm and fire suppression acceptance testing, exterior wall sheathing) are included in the applicable visit if required by code for this project.

We offer same-day or next-business-day inspection scheduling, including evenings and weekends at the same rate with no surcharge.

Happy to jump on a quick call if it helps.
""",
    },
    {
        "label": "NHM",
        "to": "travis.boren@guardiangc.net",
        "subject": "Third-Party Code Compliance Inspection Proposal – Sanitary and Storm Systems Upgrade, National Museum of Natural History",
        "attachment": PROJECTS / "Guardian Construction Inc" / "NHM Sanitary and Storm Systems Upgrade" / "NHM Sanitary and Storm Systems Upgrade - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Travis,

Thank you for including BCC on the Smithsonian National Museum of Natural History sanitary and stormwater upgrade. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: scope is phased plumbing work across the Main Building plus East and West Wings. Applicable disciplines are Building and Plumbing (Mechanical, Electrical, and Fire Protection are not in scope for this task). Aggressive flat rate of $325 per inspection visit.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. If phased execution requires more site visits, each is billed individually at the same rate. Items such as sprinkler hydro/flush or fire alarm testing are included only if required by code for this scope.

We offer same-day or next-business-day inspection scheduling, including evenings and weekends at the same rate with no surcharge. Given the historic and operating-museum context, we are glad to coordinate visit timing around exhibit and research-operation constraints.

Happy to discuss any questions on the proposal or phasing.
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
        print(f"[GUARD] already sent once (marker {MARKER.name}). Refusing re-send.")
        sys.exit(1)
    for em in EMAILS:
        if not em["attachment"].exists():
            print(f"[FAIL] attachment missing: {em['attachment']}")
            continue
        ok, msg = send_from_admin_with_attachment(
            to_email=em["to"],
            subject=em["subject"],
            body_plain=em["body"],
            attachment_path=str(em["attachment"]),
        )
        print(f"{'SENT' if ok else 'FAIL'} → {em['to']}: {msg}")
    MARKER.write_text("sent 2026-04-22")
    print(f"[marker written: {MARKER.name}]")


if __name__ == "__main__":
    main()
