"""Send 4 proposals (QCIM / Panda Express / NARA Turnkey / Room Reno). GUARDED."""
import sys
from pathlib import Path
from email_sender import send_from_admin_with_attachment

BASE = Path(__file__).resolve().parent
PROJECTS = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")
MARKER = BASE / ".send_qcim_panda_naraT_roomreno_20260423.marker"

EMAILS = [
    {
        "label": "GPO QCIM (Desbuild)",
        "to": "natasha.solis@desbuild.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – US GPO QCIM Room Renovation (732 N Capitol St NW)",
        "attachment": PROJECTS / "Desbuild, Inc" / "US GPO QCIM Room Renovation - Washington, DC" / "US GPO QCIM Room Renovation - Washington, DC - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Natasha,

Thank you for the opportunity to bid on the US GPO QCIM Room Renovation at 732 North Capitol Street NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: full 5-discipline (Building, Mechanical, Electrical, Plumbing, Fire Protection) Third-Party Code Compliance Inspection for the adhesive mixing room refurbishment. Given the contained single-room scope (ceiling duct removal, new mixer rough-in, finishes refresh), our estimate is 2 inspection visits — one close-in for the new mixer electrical rough-in and ceiling duct / MEP modifications, one combo final — at a flat rate of $325 per visit.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The 2-visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. If additional visits are needed due to phasing or expanded scope, each is billed individually at the same rate.

We offer same-day or next-business-day inspection scheduling at the same rate.

Happy to answer any questions on the proposal.
""",
    },
    {
        "label": "Panda Express (Parkway)",
        "to": "jwhiting@pkwycon.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – Panda Express (1247 1st St SE, Navy Yard)",
        "attachment": PROJECTS / "Parkway Construction" / "Panda Express - Washington, DC" / "Panda Express - Washington, DC - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Jeff,

Thank you for the opportunity to bid on the Panda Express remodel at 1247 1st Street SE in the Navy Yard / Ballpark district. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: full 5-discipline (Building, Mechanical, Electrical, Plumbing, Fire Protection) Third-Party Code Compliance Inspection for the 2,323 SF commercial kitchen fit-out. Our estimate is 4 inspection visits — underground plumbing (ground-floor restaurant with grease line), combo close-in covering MEP rough-in plus grease duct light test and sprinkler hydro/flush test, and combo final including fire alarm / FP acceptance testing — at a flat rate of $350 per visit.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The 4-visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront.

We offer same-day or next-business-day inspection scheduling at the same rate.

Happy to discuss phasing or any specific triggers in the permit set.
""",
    },
    {
        "label": "NARA Turnkey (Capital Trades)",
        "to": "epalma@capitaltradesva.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – GPO NARA 4th Floor Turnkey Interior Buildout (732 N Capitol St NW)",
        "attachment": PROJECTS / "Capital Trades, LLC" / "GPO NARA 4th Floor Renovation - Turnkey Interior Buildout" / "GPO NARA 4th Floor Renovation - Turnkey Interior Buildout - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Esthuardo,

Thank you for including BCC on the GPO NARA 4th Floor Turnkey Interior Buildout at 732 North Capitol Street NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: full 5-discipline (Building, Mechanical, Electrical, Plumbing, Fire Protection) Third-Party Code Compliance Inspection. Aggressive flat rate of $325 per inspection visit on this approximately 46,750 SF / 18-month scope. Because the A&E documents phase the work into Phase 1 and Phase 2, our estimate reflects two-phase close-in (MEP rough-in, framing, wall / ceiling close-in, sprinkler hydro/flush test, fire alarm / low-voltage rough-in) and two-phase final (including fire alarm and FP system acceptance testing) passes, for a total of 7 visits.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The 7-visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. Given the extended duration and multi-phase nature, the actual visit count will adjust to the contractor's pour / close-in / energization milestones.

We offer same-day or next-business-day inspection scheduling at the same rate, including evenings and weekends with no surcharge.

Happy to discuss phasing, A&E document coordination, or any questions on the proposal.
""",
    },
    {
        "label": "Room Reno (G3 Contracting)",
        "to": "cmcbride@g3-contracting.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – Room Renovation Washington DC (732 N Capitol St NW)",
        "attachment": PROJECTS / "G3 Contracting Solutions Inc" / "Room Renovation Washington DC - Division 02 Demolition" / "Room Renovation Washington DC - Division 02 Demolition - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Cameron,

Thank you for the opportunity to support G3 Contracting on the Room Renovation Washington DC project at 732 North Capitol Street NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: full 5-discipline (Building, Mechanical, Electrical, Plumbing, Fire Protection) Third-Party Code Compliance Inspection for the Division 02 Demolition / interior room reno scope. Our estimate is 3 inspection visits — combo close-in (MEP rough-in plus sprinkler hydro/flush test if required by code) and combo final (plus fire alarm / FP acceptance testing if required) — at a flat rate of $350 per visit.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The 3-visit count in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. If additional visits are needed due to phasing or expanded scope, each is billed individually at the same rate.

We offer same-day or next-business-day inspection scheduling at the same rate.

Happy to answer any questions on the proposal or on BCC's approach to federal prevailing-wage projects.
""",
    },
]


def main():
    if "--dry-run" in sys.argv:
        for em in EMAILS:
            print(f"\n=== {em['label']} ===\nTo: {em['to']}\nSubject: {em['subject']}\nAttachment: {em['attachment']}\nBody:\n{em['body']}")
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
        print(f"{'SENT' if ok else 'FAIL'} -> {em['to']}: {msg}")
    MARKER.write_text("sent 2026-04-23")
    print(f"[marker: {MARKER.name}]")


if __name__ == "__main__":
    main()
