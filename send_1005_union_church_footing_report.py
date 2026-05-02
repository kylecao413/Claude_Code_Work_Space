"""Send 1005 Union Church Rd footing/foundation FAIL report (.txt) to owner.

Approved by Kyle 2026-04-30. Sender: ycao@kcyengineer.com. No CC (KCY brand).
"""
from pathlib import Path
from core_tools.active_operator import operator_lock
from email_sender import send_from_kcy_with_attachment

TXT_PATH = Path(
    r"C:\Users\Kyle Cao\VA Business\VA Business\Fairfax County Residential TPI Application"
    r"\Project\1005 Union Church Rd, Mclean, VA 22102"
    r"\1005 Union Church Rd McLean VA - Footing Foundation Inspection Report 04-30-2026.txt"
)

SUBJECT = ("1005 Union Church Rd -- Footing/Foundation Inspection 04/30/2026 "
           "-- FAIL (6 deficiencies, with corrective actions)")

BODY = """Hi Hafiz,

I performed the footing/foundation pre-pour inspection at 1005 Union Church Rd, McLean, VA 22102 today (04/30/2026) at 2:00 PM. The inspection FAILED with 6 deficiencies. Please share this with your contractor and the Engineer of Record (EOR) -- concrete should NOT be poured until every item is corrected and a re-inspection passes.

Summary (full report attached as .txt with code citations + corrective methods):

1. Trench has standing water/mud/roots -- must be cleaned to firm undisturbed soil before pour. (VRC R403.1.4)
2. Rebar grid resting on soil -- must be lifted onto chairs/dobies for 3 in concrete cover. (ACI 318 20.6.1.3.1 via VRC R404)
3. L-shaped vertical dowels missing or not tied to the horizontal footing bars -- must be installed and tied BEFORE the pour, lap = 40 bar diameters per the approved drawings.
4. Verify footing geometry against the approved drawings: 2'-6 wide x 12 thick with (3) #5 longitudinal bars continuous, splices staggered and properly lapped.
5. Stepped footing detail is not on the approved drawings. Need the EOR to issue a signed/sealed stepped-footing detail (riser, run, reinforcement continuity through steps) before re-inspection. (VRC R403.1.5)
6. Verify bottom-of-footing extends >= 24 in below finished exterior grade everywhere (Fairfax County frost depth = 24 in, including the shallowest step).

Once all six items are corrected and any required EOR sealed detail is on site, please reply to this email and I will schedule the re-inspection.

Best,
Yue Cao, PE
KCY Engineering Code Consulting, LLC
571-365-6937 | ycao@kcyengineer.com
"""

if __name__ == "__main__":
    assert TXT_PATH.is_file(), TXT_PATH
    with operator_lock(Path(__file__).name):
        ok, info = send_from_kcy_with_attachment(
            to_email="hsalihi@geotransrail.com",
            subject=SUBJECT,
            body_plain=BODY,
            attachment_path=str(TXT_PATH),
        )
        print("OK" if ok else "FAIL", info)
