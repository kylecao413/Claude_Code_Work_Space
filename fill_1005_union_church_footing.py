"""Fill Fairfax residential TPI Foundation report for 1005 Union Church Rd.

Inspection performed 2026-04-30 14:00:
  - Footing/Foundation pre-pour: FAIL (6 deficiencies)

References: 2021 VRC + ACI 318-19 (via VRC R404) + Fairfax local frost (24").
Stamps Yue Cao's E-Sig.jpg over the page-3 Signature line and flattens to a
non-editable image-only PDF for Fairfax County submission.
"""
from pathlib import Path
import fitz
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

SIGNATURE_IMG = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Logo E-Sig Stamp\E-Sig.jpg")

PROJECT_DIR = Path(
    r"C:\Users\Kyle Cao\VA Business\VA Business\Fairfax County Residential TPI Application\Project\1005 Union Church Rd, Mclean, VA 22102"
)
TEMPLATE_DIR = Path(
    r"C:\Users\Kyle Cao\VA Business\VA Business\Fairfax County Residential TPI Application\Report forms"
)

FIRM = {
    "Company Name": "KCY Engineering Code Consulting LLC",
    "Telephone": "571-365-6937",
    "Address": "3914 Tallow Tree Ct, Fairfax, VA 22033",
}
PERMIT_ADDRESS = "1005 Union Church Rd, Mclean, VA 22102"
PERMIT_NUM = "ALTR-2025-00341"
BUILDER = "Salihi Hafizullah"
NAME_PRINTED = "Yue Cao"
INSP_DATE = "04/30/2026"
INSP_TIME = "14:00"


def _ascii_safe(s):
    if not isinstance(s, str):
        return s
    return (s.replace("—", "--").replace("–", "-")
             .replace("≈", "~").replace("≥", ">=").replace("≤", "<=")
             .replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"')
             .replace("Ø", "dia").replace("×", "x"))


def write_filled(src, dst, values):
    reader = PdfReader(str(src))
    writer = PdfWriter(clone_from=reader)
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
    fields = {k: _ascii_safe(v) for k, v in values.items()}
    for page in writer.pages:
        writer.update_page_form_field_values(page, fields)
    with open(dst, "wb") as f:
        writer.write(f)
    print(f"Wrote {dst.name}")


# 10-line comment block (each line ~95 chars to fit AcroForm underline).
comments = [
    "Footing pre-pour FAILED -- 6 deficiencies. Do NOT pour concrete until all items corrected.",
    "D1 Subgrade (VRC R403.1.4): standing water/mud/roots -- dewater + remove debris to firm soil.",
    "D2 Cover (ACI 318 20.6.1.3.1 / VRC R404): rebar on soil -- lift mat onto chairs for 3 in cover.",
    "D3 Dowels: missing/untied -- install per drawing, lap 40 db (25 in for #5), tie BEFORE pour.",
    "D4 Geometry: verify 2'-6 W x 12 thick, (3) #5 longitudinal continuous w/ 25 in staggered laps.",
    "D5 Stepped footing (VRC R403.1.5): bottom slope >1:10 needs step; EOR sealed step detail not on",
    "   drawings -- EOR to issue (riser, run, reinf through step) before re-inspection.",
    "D6 Frost depth: Fairfax requires >=24 in below finished grade everywhere (incl shallowest step).",
    "Re-inspect: contractor email ycao@kcyengineer.com once all 6 corrected and EOR detail on site.",
    "Pouring w/o passing re-inspection = destructive verification (cores/exposing rebar) at GC cost.",
]

fields = {
    **FIRM,
    "Permit Address": PERMIT_ADDRESS,
    "Building Permit #": PERMIT_NUM,
    "Builder": BUILDER,
    # Footing pre-pour = both Subgrade AND Forms rows fail (trench dirty + rebar/dowel issues)
    "Footings (Record # of Piers):Subgrade": "Fail",
    "Footings (Record # of Piers):Subgrade_1": INSP_DATE,
    "Footings (Record # of Piers):Subgrade_2": INSP_TIME,
    "Footings (Record # of Piers):Forms": "Fail",
    "Footings (Record # of Piers):Forms_1": INSP_DATE,
    "Footings (Record # of Piers):Forms_2": INSP_TIME,
    # Page 3 signature block
    "Name printed": NAME_PRINTED,
    "Date": INSP_DATE,
}
for i, line in enumerate(comments):
    key = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
    fields[key] = line

interim_fill = PROJECT_DIR / "third-party-inspections-building-foundation.pdf"
write_filled(
    TEMPLATE_DIR / "third-party-inspections-building-foundation.pdf",
    interim_fill,
    fields,
)


def stamp_and_flatten(filled_pdf: Path, final_pdf: Path):
    """Stamp E-Sig.jpg over the Signature line, then flatten to image-only PDF."""
    doc = fitz.open(filled_pdf)
    # Find the page with the "Signature:" label dynamically
    sig_page = None
    sig_label = None
    for page in doc:
        matches = page.search_for("Signature:")
        if matches:
            sig_page = page
            sig_label = matches[0]
            break
    if sig_page is None:
        raise RuntimeError(f"Could not locate 'Signature:' label in {filled_pdf.name}")

    x0 = sig_label.x1 + 6
    y_center = (sig_label.y0 + sig_label.y1) / 2
    sig_rect = fitz.Rect(x0, y_center - 14, x0 + 160, y_center + 14)
    sig_page.insert_image(sig_rect, filename=str(SIGNATURE_IMG), keep_proportion=True)

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


REPORT_DATE_TAG = "04-30-2026"
PROJECT_TAG = "1005 Union Church Rd McLean VA"

stamp_and_flatten(
    interim_fill,
    PROJECT_DIR / f"{PROJECT_TAG} - Footing Foundation Inspection Report {REPORT_DATE_TAG}.pdf",
)
print("Done. Signed non-editable PDF ready for Fairfax submission.")
