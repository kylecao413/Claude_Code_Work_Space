"""Fill Fairfax residential TPI report PDFs for 3303 Lockheed Blvd project.

Concealment inspections performed 2026-04-25:
  - Mechanical: PASS (wall-mount split system, no concealed refrigerant/condensate runs)
  - Electrical: FAIL (outlet spacing + cable support violations)
  - Building : FAIL (air seal, hurricane ties, guard ballister spacing)

References: 2021 VRC (Virginia Residential Code) + 2020 NEC adopted via VRC.

Stamps Yue Cao's E-Sig.jpg over the page-2 Signature line and flattens each
report to an image-only, non-editable PDF for Fairfax County submission.
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
INSP_DATE = "04/25/2026"


def _ascii_safe(s):
    if not isinstance(s, str):
        return s
    return (s.replace("—", "--")  # em dash
             .replace("–", "-")    # en dash
             .replace("≈", "~")    # approx
             .replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"'))


def write_filled(src: Path, dst: Path, values: dict, clear_extras: list[str] = None):
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
# MECHANICAL - PASS (wall-mount mini-split)
# ============================================================
mech_comments = [
    "Mechanical concealment inspection for the building addition is APPROVED.",
    "Scope: single wall-mounted ductless mini-split indoor unit; matching outdoor condensing unit",
    "set on grade directly outside the nearest exterior wall (shortest run).",
    "Refrigerant lineset, condensate drain, and low-voltage control wiring pass only through the",
    "exterior wall sleeve at the indoor head -- NO concealed ductwork, no concealed refrigerant",
    "joints, and no concealed condensate routing within wall or ceiling cavities.",
    "Lineset penetration sleeved + sealed; condensate to exterior at grade with required air gap;",
    "outdoor unit on level pad with manufacturer service clearances maintained.",
    "Code refs: 2021 VRC M1411 (refrigerant piping), M1411.3 (condensate), M1411.6 (locking caps);",
    "2020 NEC 440.14 (disconnect within sight). PASS -- approved to proceed with wall close-in.",
]
mech_fields = {
    **FIRM,
    "Permit Address": PERMIT_ADDRESS,
    "Building Permit #": "MECHR-2025-03296",
    "Name printed": NAME_PRINTED,
    "Date": INSP_DATE,
    # Inspection table
    "Mechanical Concealment": "Pass",
    "Mechanical Concealment_1": INSP_DATE,
    "Mechanical Concealment_2": "10:30",
}
for i, line in enumerate(mech_comments):
    key = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
    mech_fields[key] = line
write_filled(
    TEMPLATE_DIR / "third-party-inspections-building-mechanical.pdf",
    PROJECT_DIR / "third-party-inspections-building-mechanical.pdf",
    mech_fields,
)


# ============================================================
# ELECTRICAL - FAIL (receptacle spacing + cable support)
# ============================================================
elec_comments = [
    "Electrical concealment inspection for the building addition FAILED -- 2 deficiencies.",
    "DEFICIENCY #1 -- Receptacle outlet spacing along the new addition wall line.",
    "Measured spacing between adjacent 125V 15/20A receptacles exceeds 12 ft on-center,",
    "leaving wall space > 6 ft from a receptacle. Per 2020 NEC 210.52(A)(1), no point",
    "along the floor line of any wall space shall be more than 6 ft from a receptacle outlet.",
    "Action: add at least 2 additional receptacle outlets in the deficient wall sections.",
    "DEFICIENCY #2 -- NM-B cable support / securement at new outlet locations.",
    "Per 2020 NEC 334.30: NM cable secured at intervals <= 4.5 ft AND within 12 in of every",
    "box (8 in for single-gang nonmetallic boxes per 314.17(B)(1) where stapled). Add staples.",
    "Re-inspection required. Do NOT close in walls in affected areas until corrected.",
]
elec_fields = {
    **FIRM,
    "Permit Address": PERMIT_ADDRESS,
    "Building Permit #": "ELER-2025-07056",
    "Name printed": NAME_PRINTED,
    "Date": INSP_DATE,
    # Inspection table - Electrical Concealment row
    "Electrical Concealment": "Fail",
    "Electrical Concealment_1": INSP_DATE,
    "Electrical Concealment_2": "10:45",
    # clear stale "Other:" leftover row from earlier draft
    "Other": "",
    "Pool Structural Steel Bonding_1": "",
    "Pool Structural Steel Bonding_3": "",
    "Pool Structural Steel Bonding_5": "",
}
for i, line in enumerate(elec_comments):
    key = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
    elec_fields[key] = line
write_filled(
    PROJECT_DIR / "third-party-inspections-building-electrical.pdf",
    PROJECT_DIR / "third-party-inspections-building-electrical.pdf",
    elec_fields,
)


# ============================================================
# BUILDING - FAIL (air seal, hurricane ties, guard balusters)
# ============================================================
bldg_comments = [
    "Building wall/ceiling close-in inspection for the addition FAILED -- 3 deficiencies.",
    "DEFICIENCY #1 -- Exterior envelope air sealing. Penetrations at exterior-wall electrical",
    "outlet boxes and gaps around new window rough-openings are NOT air sealed.",
    "Per 2021 VRC N1102.4.1.1 / Table N1102.4.1.1 (Air Barrier + Insulation Installation):",
    "seal jamb-to-framing gaps and air-seal exterior-wall outlet boxes (or use gasketed boxes).",
    "DEFICIENCY #2 -- Roof tie-down: 2 hurricane tie connectors missing at rafter-to-top-plate",
    "(3rd and 5th rafter from south end -- field marked). Per 2021 VRC R802.11 / Table R802.11,",
    "install Simpson H2.5A (or equiv) at every rafter w/ manufacturer's full nailing schedule.",
    "DEFICIENCY #3 -- Exterior stair guard baluster spacing > 4 in clear (walking surface > 30 in",
    "above grade). Per 2021 VRC R312.1.3, guard openings shall not pass a 4-in sphere. Re-space.",
]
bldg_fields = {
    **FIRM,
    "Permit Address": PERMIT_ADDRESS,
    "Building Permit #": "ALTR-2025-02910",
    "Name printed": NAME_PRINTED,
    "Date": INSP_DATE,
    # Inspection table - Wall/Ceiling Close In row
    "Wall/Ceiling Close In": "Fail",
    "Wall/Ceiling Close In_1": INSP_DATE,
    "Wall/Ceiling Close In_2": "11:00",
}
for i, line in enumerate(bldg_comments):
    key = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
    bldg_fields[key] = line
write_filled(
    PROJECT_DIR / "third-party-inspections-building.pdf",
    PROJECT_DIR / "third-party-inspections-building.pdf",
    bldg_fields,
)

print("All 3 fillable PDFs written. Now stamping signature + flattening...")


def stamp_and_flatten(filled_pdf: Path, final_pdf: Path):
    """Stamp E-Sig.jpg over page-2 Signature line, then flatten to image-only PDF."""
    doc = fitz.open(filled_pdf)
    page2 = doc[1]
    # Locate the "Signature:" label dynamically — its Y differs per template
    # (Mechanical has a shorter inspection table than Building/Electrical, so
    # the signature box sits lower on the page). Anchor the image to whatever
    # rect search_for returns, then offset to overlay the underline to the right.
    matches = page2.search_for("Signature:")
    if not matches:
        raise RuntimeError(f"Could not locate 'Signature:' label in {filled_pdf.name}")
    sig_label = matches[0]
    # Place image immediately to the right of "Signature:" label, sitting on the underline.
    # Image height ~ 1.3x label height; width ~ 160 pt is enough for the e-sig.
    x0 = sig_label.x1 + 6      # 6pt gap after the colon
    y_center = (sig_label.y0 + sig_label.y1) / 2
    sig_rect = fitz.Rect(x0, y_center - 14, x0 + 160, y_center + 14)
    page2.insert_image(sig_rect, filename=str(SIGNATURE_IMG), keep_proportion=True)
    interim = filled_pdf.with_suffix(".interim.pdf")
    doc.save(interim)
    doc.close()

    # Flatten: render each page at 250 DPI into a brand-new image-only PDF.
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


REPORT_DATE_TAG = "04-25-2026"
PROJECT_TAG = "3303 Lockheed Blvd Alexandria VA"

stamp_and_flatten(
    PROJECT_DIR / "third-party-inspections-building-mechanical.pdf",
    PROJECT_DIR / f"{PROJECT_TAG} - Mechanical Concealment Report {REPORT_DATE_TAG}.pdf",
)
stamp_and_flatten(
    PROJECT_DIR / "third-party-inspections-building-electrical.pdf",
    PROJECT_DIR / f"{PROJECT_TAG} - Electrical Concealment Report {REPORT_DATE_TAG}.pdf",
)
stamp_and_flatten(
    PROJECT_DIR / "third-party-inspections-building.pdf",
    PROJECT_DIR / f"{PROJECT_TAG} - Building Concealment Report {REPORT_DATE_TAG}.pdf",
)

print("Done. 3 signed non-editable PDFs ready for Fairfax submission.")
