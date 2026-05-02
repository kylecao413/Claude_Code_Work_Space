"""Flatten every PDF in the 1522 RIA NE Wrap up folder to non-editable form
(250 DPI rasterize per page → new PDF). Universal rule for DOB / county / city
submittals — no AcroForm fields, no annotations, no underlying text.

Per Kyle (2026-04-28): all submittal PDFs must be flattened. Signature images
embedded in the source template (e.g. page 61 of the Third-Party Procedure
Manual already carries Yue's signature in the SIGNATURE_3 appearance) bake into
the rasterized output automatically.
"""
from __future__ import annotations
from pathlib import Path
import fitz

WRAP = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Nery Soto Fire Protection\1522 Rhode Island Ave NE - PR\Wrap up")
DPI = 250

TARGETS = [
    "Approved_1522_Rhode_Island_Ave_NE_SPK__FA_PR_NOI_signed.pdf",
    "1522 Rhode Island Ave NE SPK Plan Review Deficiency Report.pdf",
    "1522 Rhode Island Ave NE FA Plan Review Deficiency Report.pdf",
    "1522 Rhode Island Ave NE FP Plan Review Approval Certificate and Report.pdf",
    "1522 Rhode Island Ave NE Plan Review Certification Letter.pdf",
    "Large Stamp for 1522 Rhode Island Ave NE FP review.pdf",
]


def flatten_pdf(src_path: Path, out_path: Path, dpi: int = DPI) -> None:
    src = fitz.open(src_path)
    out = fitz.open()
    for page in src:
        # Render page at target DPI. 72 pt = 1 inch baseline.
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        # New page sized in points so pix maps 1:1 visually
        w_pt = pix.width * 72.0 / dpi
        h_pt = pix.height * 72.0 / dpi
        new_page = out.new_page(width=w_pt, height=h_pt)
        new_page.insert_image(fitz.Rect(0, 0, w_pt, h_pt), pixmap=pix)
    src.close()
    # garbage=4 cleans, deflate compresses, no_new_id keeps it stable for hashing
    out.save(out_path, garbage=4, deflate=True)
    out.close()


def has_widgets(path: Path) -> int:
    """Count interactive form widgets across all pages."""
    d = fitz.open(path); n = 0
    for page in d:
        n += len(list(page.widgets() or []))
    d.close()
    return n


def main():
    locked = []
    for fn in TARGETS:
        src = WRAP / fn
        if not src.exists():
            print(f"[skip] {fn}  (not found)")
            continue
        before = has_widgets(src)
        tmp = src.with_suffix(".flat.pdf")
        flatten_pdf(src, tmp)
        after = has_widgets(tmp)
        sz_before = src.stat().st_size; sz_after = tmp.stat().st_size
        try:
            src.unlink()
            tmp.rename(src)
            print(f"[ok] {fn}  widgets {before}->{after}  size {sz_before//1024}KB->{sz_after//1024}KB")
        except PermissionError:
            print(f"[LOCKED] {fn}  cannot replace - file open in another process. Flat version left at {tmp.name}")
            locked.append(fn)
    if locked:
        print()
        print("Close these files in Acrobat/Preview/etc., then re-run this script:")
        for fn in locked:
            print(f"  - {fn}")


if __name__ == "__main__":
    main()
