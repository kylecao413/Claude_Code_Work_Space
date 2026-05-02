"""Fill Fairfax residential TPI re-inspection report PDFs for 3303 Lockheed Blvd.

Re-inspections performed 2026-04-29 17:00 (Mechanical skipped -- already passed
on 2026-04-25). Both previously-failed trades now PASS:
  - Electrical: PASS (210.52(A)(1) and 334.30 deficiencies corrected)
  - Building  : PASS (N1102.4.1.1, R802.11, R312.1.3 deficiencies corrected)

Code refs: 2021 Virginia Residential Code (VRC) and 2020 NEC adopted via VRC.
"""
from pathlib import Path
import fitz
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

SIGNATURE_IMG = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Logo E-Sig Stamp\E-Sig.jpg")

PROJECT_DIR = Path(
    r"C:\Users\Kyle Cao\VA Business\VA Business\Fairfax County Residential TPI Application\Project\3303 Lockheed Blvd, Alexandria, VA 22306"
)
TEMPLATE_DIR = Path(
    r"C:\Users\Kyle Cao\VA Business\VA Business\Fairfax County Residential TPI Application\Report forms"
)

FIRM = {
    "Company Name": "KCY Engineering Code Consulting LLC",
    "Telephone": "571-365-6937",
    "Address": "3914 Tallow Tree Ct, Fairfax, VA 22033",
}
PERMIT_ADDRESS = "3303 Lockheed Blvd, Alexandria, VA 22306"
NAME_PRINTED = "Yue Cao"
INSP_DATE = "04/29/2026"
INSP_TIME = "17:00"


def _ascii_safe(s):
    if not isinstance(s, str):
        return s
    return (s.replace("—", "--")
             .replace("–", "-")
             .replace("≈", "~")
             .replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"'))


def write_filled(src: Path, dst: Path, values: dict, clear_extras=None):
    reader = PdfReader(str(src))
    writer = PdfWriter(clone_from=reader)
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
    fields_to_set = {k: _ascii_safe(v) for k, v in values.items()}
    for name in (clear_extras or []):
        fields_to_set[name] = ""
    for page in writer.pages:
        writer.update_page_form_field_values(page, fields_to_set)
    with open(dst, "wb") as f:
        writer.write(f)
    print(f"Wrote {dst.name}")


# ============================================================
# ELECTRICAL - RE-INSPECTION PASS
# ============================================================
elec_comments = [
    "Electrical concealment RE-INSPECTION for the building addition is APPROVED.",
    "Original inspection 2026-04-25 cited 2 deficiencies; both corrected and verified",
    "on site this date prior to wall close-in.",
    "ITEM #1 (CORRECTED) -- Receptacle outlet spacing along addition wall line.",
    "Two (2) additional 125V 15A receptacle outlets installed in the previously deficient",
    "wall sections; spacing now satisfies 2020 NEC 210.52(A)(1) -- no point along the",
    "floor line of any wall space more than 6 ft from a receptacle. Field-measured.",
    "ITEM #2 (CORRECTED) -- NM-B cable securement.",
    "NM cable now secured with staples within 12 in of every box and at intervals not",
    "exceeding 4.5 ft, per 2020 NEC 334.30. Verified at all new outlet locations.",
    "All previously cited deficiencies have been corrected. PASS -- approved for close-in.",
]
elec_fields = {
    **FIRM,
    "Permit Address": PERMIT_ADDRESS,
    "Building Permit #": "ELER-2025-07056",
    "Name printed": NAME_PRINTED,
    "Date": INSP_DATE,
    "Electrical Concealment": "Pass",
    "Electrical Concealment_1": INSP_DATE,
    "Electrical Concealment_2": INSP_TIME,
    "Other": "",
    "Pool Structural Steel Bonding_1": "",
    "Pool Structural Steel Bonding_3": "",
    "Pool Structural Steel Bonding_5": "",
}
for i, line in enumerate(elec_comments):
    key = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
    elec_fields[key] = line

write_filled(
    TEMPLATE_DIR / "third-party-inspections-building-electrical.pdf",
    PROJECT_DIR / "third-party-inspections-building-electrical_reinspection.pdf",
    elec_fields,
)


# ============================================================
# BUILDING - RE-INSPECTION PASS
# ============================================================
bldg_comments = [
    "Building wall/ceiling close-in RE-INSPECTION for the addition is APPROVED.",
    "Original inspection 2026-04-25 cited 3 deficiencies; all corrected and verified on",
    "site this date prior to wall close-in.",
    "ITEM #1 (CORRECTED) -- Exterior envelope air sealing.",
    "Penetrations at exterior-wall outlet boxes and gaps around new window rough-openings",
    "are now fully air-sealed with foam/sealant; outlet boxes gasketed. Compliant with",
    "2021 VRC N1102.4.1.1 and Table N1102.4.1.1 (Air Barrier + Insulation Installation).",
    "ITEM #2 (CORRECTED) -- Roof tie-down at rafter-to-top-plate.",
    "Two (2) Simpson H2.5A hurricane tie connectors installed at the previously missing",
    "locations (3rd and 5th rafter from south end), per manufacturer's full nailing",
    "schedule. Compliant with 2021 VRC R802.11 / Table R802.11.",
    "ITEM #3 (CORRECTED) -- Exterior stair guard baluster spacing.",
    "Balusters re-spaced; openings now do not allow passage of a 4-in sphere, per 2021",
    "VRC R312.1.3. Verified by sphere test.",
    "All previously cited deficiencies have been corrected. PASS -- approved for close-in.",
]
bldg_fields = {
    **FIRM,
    "Permit Address": PERMIT_ADDRESS,
    "Building Permit #": "ALTR-2025-02910",
    "Name printed": NAME_PRINTED,
    "Date": INSP_DATE,
    "Wall/Ceiling Close In": "Pass",
    "Wall/Ceiling Close In_1": INSP_DATE,
    "Wall/Ceiling Close In_2": INSP_TIME,
}
for i, line in enumerate(bldg_comments):
    key = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
    bldg_fields[key] = line

write_filled(
    TEMPLATE_DIR / "third-party-inspections-building.pdf",
    PROJECT_DIR / "third-party-inspections-building_reinspection.pdf",
    bldg_fields,
)

print("Both fillable re-inspection PDFs written. Now stamping signature + flattening...")


def stamp_and_flatten(filled_pdf: Path, final_pdf: Path):
    doc = fitz.open(filled_pdf)
    page2 = doc[1]
    matches = page2.search_for("Signature:")
    if not matches:
        raise RuntimeError(f"Could not locate 'Signature:' label in {filled_pdf.name}")
    sig_label = matches[0]
    x0 = sig_label.x1 + 6
    y_center = (sig_label.y0 + sig_label.y1) / 2
    sig_rect = fitz.Rect(x0, y_center - 14, x0 + 160, y_center + 14)
    page2.insert_image(sig_rect, filename=str(SIGNATURE_IMG), keep_proportion=True)
    interim = filled_pdf.with_suffix(".interim.pdf")
    doc.save(interim)
    doc.close()

    src = fitz.open(interim)
    out = fitz.open()
    for page in src:
        pix = page.get_pixmap(dpi=250, alpha=False)
        rect = page.rect
        new_page = out.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)
    src.close()
    out.save(final_pdf, deflate=True, garbage=4)
    out.close()
    interim.unlink(missing_ok=True)
    print(f"  -> {final_pdf.name} (signed + flattened, non-editable)")


REPORT_DATE_TAG = "04-29-2026"
PROJECT_TAG = "3303 Lockheed Blvd Alexandria VA"

stamp_and_flatten(
    PROJECT_DIR / "third-party-inspections-building-electrical_reinspection.pdf",
    PROJECT_DIR / f"{PROJECT_TAG} - Electrical Concealment Re-Inspection Report {REPORT_DATE_TAG}.pdf",
)
stamp_and_flatten(
    PROJECT_DIR / "third-party-inspections-building_reinspection.pdf",
    PROJECT_DIR / f"{PROJECT_TAG} - Building Concealment Re-Inspection Report {REPORT_DATE_TAG}.pdf",
)

print("Done. 2 signed non-editable PDFs ready for Fairfax submission.")
