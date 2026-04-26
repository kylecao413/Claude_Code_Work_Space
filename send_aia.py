"""Send AIA HQ proposal. GUARDED."""
import sys
from pathlib import Path
from email_sender import send_from_admin_with_attachment

BASE = Path(__file__).resolve().parent
PROJECTS = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")
MARKER = BASE / ".send_aia_20260423.marker"

TO = "amiles@tcco.com"
SUBJECT = "Third-Party Code Compliance Inspection Proposal – AIA Headquarters Renewal, 1735 New York Ave NW"
ATTACHMENT = PROJECTS / "Turner Construction Company" / "AIA Headquarters Renovation" / "AIA Headquarters Renovation - Third Party Code Inspection Proposal from BCC.pdf"
BODY = """Hi Akilah,

Thank you for the opportunity to bid on the AIA Headquarters Renewal at 1735 New York Ave NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: full 5-discipline (Building, Mechanical, Electrical, Plumbing, Fire Protection) Third-Party Code Compliance Inspection for the Lower Level plus Levels 1-4 full renovation; limited scope on tenant-occupied Levels 5-7 (perimeter mechanical, core-restroom plumbing, storm drain routing) and rooftop MEP platform and PV. Aggressive flat rate of $325 per inspection visit.

Billing approach: BCC's invoice is fully based on the number of actual combo-inspection visits conducted. The 7-visit estimate in Exhibit C is a reference only — never a cap, never bundled, never billed upfront. Each visit performed is invoiced separately at the flat per-visit rate. Given the structural scope (rooftop platform, Level 1/4 atrium and stair openings, 2 feature stairs, façade modernization) and the phased renovation across 5 full-reno floors, actual visit count will follow the contractor's milestones. Items such as sprinkler hydro/flush test, fire alarm and fire suppression acceptance testing, and exterior wall sheathing are included in the applicable visit if required by code for this scope.

We offer same-day or next-business-day inspection scheduling, including evenings and weekends at the same rate with no surcharge.

Happy to walk through the proposal, phasing, or structural observation coordination.
"""


def main():
    if "--dry-run" in sys.argv:
        print(f"To: {TO}\nSubject: {SUBJECT}\nBody:\n{BODY}")
        return
    if MARKER.exists():
        print(f"[GUARD] already sent (marker {MARKER.name}).")
        sys.exit(1)
    if not ATTACHMENT.exists():
        print(f"[FAIL] attachment missing: {ATTACHMENT}")
        sys.exit(1)
    ok, msg = send_from_admin_with_attachment(
        to_email=TO, subject=SUBJECT, body_plain=BODY, attachment_path=str(ATTACHMENT)
    )
    print(f"{'SENT' if ok else 'FAIL'} → {TO}: {msg}")
    MARKER.write_text("sent 2026-04-23")
    print(f"[marker: {MARKER.name}]")


if __name__ == "__main__":
    main()
