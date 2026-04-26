"""Fill DOB Third-Party Plan Review NOI for 1522 Rhode Island Ave NE.

Source: 76-page DC Third-Party Plan Review Program Procedure Manual PDF.
The actual NOI form is pages 1-2; we fill Section A applicant fields and
extract just those two pages for the owner to sign.
"""
from pathlib import Path
from pypdf import PdfReader, PdfWriter

SRC = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Marketing\Plan Review NOI Template.pdf")
DST_DIR = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Nery Soto Fire Protection\1522 Rhode Island Ave NE - PR")
DST = DST_DIR / "1522 Rhode Island Ave NE Plan Review NOI.pdf"

# === FILL IN BEFORE SENDING TO OWNER ===
APPLICANT_NAME = ""        # e.g. "John Smith" — property owner
PROJECT_NAME = ""          # e.g. "1522 RI Ave LLC" — owner's project entity
PROJECT_ADDRESS = "1522 Rhode Island Ave NE"
APPLICANT_TITLE = "Owner"  # printed in Section D
# ========================================

FIELDS = {
    # Section A — Applicant Information (pre-fill what we know)
    "APPLICANT NAME": APPLICANT_NAME,
    "PROJECT NAME": PROJECT_NAME,
    "PROJECT ADDRESS": PROJECT_ADDRESS,
    # Section D — Acknowledgements (applicant side, owner signs here)
    "APPLICANT NAME_2": APPLICANT_NAME,
    "APPLICANT TITLE": APPLICANT_TITLE,
    # Section B/C BCC fields are already baked into the template — no need to override.
}


def main():
    DST_DIR.mkdir(parents=True, exist_ok=True)

    # Clone full template (preserves AcroForm dict so field lookups work), fill fields,
    # then drop all pages except the first two (the actual NOI form).
    writer = PdfWriter(clone_from=str(SRC))

    filled = {k: v for k, v in FIELDS.items() if v}
    if filled:
        for page in writer.pages:
            writer.update_page_form_field_values(page, filled)

    # Keep only the actual NOI form pages (54-55 in the 76-page program manual template)
    NOI_PAGES = {54, 55}
    for idx in sorted(set(range(len(writer.pages))) - NOI_PAGES, reverse=True):
        del writer.pages[idx]

    with open(DST, "wb") as f:
        writer.write(f)

    print(f"Saved: {DST}")
    print(f"  Project Address:  {PROJECT_ADDRESS}")
    print(f"  Applicant Name:   {APPLICANT_NAME or '[BLANK — fill before sending]'}")
    print(f"  Project Name:     {PROJECT_NAME or '[BLANK — fill before sending]'}")
    print(f"  Applicant Title:  {APPLICANT_TITLE}")


if __name__ == "__main__":
    main()
