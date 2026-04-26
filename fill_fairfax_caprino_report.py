"""Fill the Fairfax Residential Building Inspection Report for 4650 Caprino Ct
and flatten to a non-editable PDF.
"""
from pathlib import Path
import fitz

PROJECT_DIR = Path(r"C:\Users\Kyle Cao\VA Business\VA Business\Fairfax County Residential TPI Application\Project\4650 Caprino Ct, Fairfax, VA 22032")
TEMPLATE = PROJECT_DIR / "third-party-inspections-building.pdf"
SIGNATURE_IMG = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Logo E-Sig Stamp\E-Sig.jpg")
INTERIM = PROJECT_DIR / "_interim_filled.pdf"
OUTPUT = PROJECT_DIR / "4650 Caprino Ct Fairfax VA field report 04-22-26.pdf"

INSPECTION_DATE = "04-22-2026"
INSPECTION_TIME = "11:30 AM"

COMMENTS = (
    "Rear deck free-standing 4-column footings were observed. The deck footings has "
    "the same foundation depth as the existing building basement footing. 50\" below "
    "grade in depth and 21\" wide square footings measured onsite. Foundation bearing "
    "base is likely the same as the existing building (silty clay; observed bearing "
    "capacity appears to exceed 1500 psf, with no evidence of disturbed soil at the "
    "base). The deck footing and foundation inspection is approved."
)

# Break comments across the 10 available comment lines (roughly 95 chars per line)
def wrap_comments(text: str, max_lines: int = 10, width: int = 95) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    while len(lines) < max_lines:
        lines.append("")
    return lines[:max_lines]


def main() -> None:
    doc = fitz.open(TEMPLATE)

    # --- Page 1: comments ---
    page1 = doc[0]
    comment_lines = wrap_comments(COMMENTS)
    for i, line in enumerate(comment_lines):
        field = "Provide inspection comments here" if i == 0 else f"Provide inspection comments here_{i}"
        for w in page1.widgets() or []:
            if w.field_name == field:
                w.field_value = line
                w.update()
                break

    # --- Page 2: deck footings row + name + date ---
    page2 = doc[1]
    deck_fills = {
        "Deck Footings (Record # of Piers):Subgrade":   "Pass (4 piers)",
        "Deck Footings (Record # of Piers):Subgrade_1": INSPECTION_DATE,
        "Deck Footings (Record # of Piers):Subgrade_2": INSPECTION_TIME,
    }
    other_fills = {
        "Date": INSPECTION_DATE,
    }
    for w in page2.widgets() or []:
        if w.field_name in deck_fills:
            w.field_value = deck_fills[w.field_name]
            w.update()
        elif w.field_name in other_fills:
            w.field_value = other_fills[w.field_name]
            w.update()

    # Save interim with filled widgets
    doc.save(INTERIM)
    doc.close()

    # --- Re-open, insert signature image on page 2, then flatten by rendering ---
    doc = fitz.open(INTERIM)
    page2 = doc[1]

    # Signature line sits between "Name printed" (y~474) and "Date" (y~548).
    # Place image over the Signature: ____ line around y~500-520.
    # Name printed rect starts at x=130; mirror that start so sig aligns with other fields.
    sig_rect = fitz.Rect(130, 500, 290, 530)
    page2.insert_image(sig_rect, filename=str(SIGNATURE_IMG), keep_proportion=True)

    doc.saveIncr()
    doc.close()

    # Final flatten: render each page to image, assemble image-only PDF (non-editable)
    src = fitz.open(INTERIM)
    out = fitz.open()
    for page in src:
        pix = page.get_pixmap(dpi=250, alpha=False)
        rect = page.rect
        new_page = out.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)
    src.close()
    out.save(OUTPUT, deflate=True, garbage=4)
    out.close()

    INTERIM.unlink(missing_ok=True)
    print(f"Wrote: {OUTPUT}")


if __name__ == "__main__":
    main()
