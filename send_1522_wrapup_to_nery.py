"""Convert remaining wrap-up Word docs to PDF and prepare the deliverable
email to Nery Soto (Rexfield) for 1522 Rhode Island Ave NE.

DOES NOT auto-send. Saves a draft into Pending_Approval/Outbound/ and prints
the preview. Kyle must explicitly say 'Y' before send_with_admin_with_attachments
runs.
"""
from __future__ import annotations
import os, sys
from pathlib import Path

WRAP_DIR = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Nery Soto Fire Protection\1522 Rhode Island Ave NE - PR\Wrap up")
PENDING = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Business Automation\Pending_Approval\Outbound")
DRAFT_MD = PENDING / "1522_RIA_NE_Wrapup_to_Nery_Draft.md"

DOC4_DOCX = WRAP_DIR / "1522 Rhode Island Ave NE Plan Review Certification Letter.docx"
DOC4_PDF = WRAP_DIR / "1522 Rhode Island Ave NE Plan Review Certification Letter.pdf"
DOC5_DOCX = WRAP_DIR / "Large Stamp for 1522 Rhode Island Ave NE FP review.docx"
DOC5_PDF = WRAP_DIR / "Large Stamp for 1522 Rhode Island Ave NE FP review.pdf"

# Final 6-PDF attachment set
ATTACHMENTS = [
    WRAP_DIR / "Approved_1522_Rhode_Island_Ave_NE_SPK__FA_PR_NOI_signed.pdf",
    WRAP_DIR / "1522 Rhode Island Ave NE SPK Plan Review Deficiency Report.pdf",
    WRAP_DIR / "1522 Rhode Island Ave NE FA Plan Review Deficiency Report.pdf",
    WRAP_DIR / "1522 Rhode Island Ave NE FP Plan Review Approval Certificate and Report.pdf",
    DOC4_PDF,
    DOC5_PDF,
]

TO_EMAIL = "nery@rexfield.us"
SUBJECT = "1522 Rhode Island Ave NE — Plan Review Approval Package (DOB Submittal)"
BODY = """Hi Nery,

Good news — the third-party plan review for 1522 Rhode Island Ave NE (Sprinkler + Fire Alarm) has been approved. The DOB has issued the Notice of Approval Certification Number TPR200000-619 (acceptance date 04/21/2026).

Attached are the supporting documents for your DOB permit submittal — six PDFs total. Please submit these alongside your latest sprinkler and fire alarm drawings:

1. Approved Notification of Intent (NOI) — DOB-stamped, signed by Ulises Rodriguez (DOB Plan Reviewer)
2. SPK Plan Review Deficiency Report — initial review + corrections verified
3. FA Plan Review Deficiency Report — initial review + corrections verified
4. Plan Review Approval Certificate and Report (DOB Form) — signed
5. Plan Review Certification Letter — addressed to DOB / Mayda Colon
6. Large Stamp — Construction Codes Verified, Fire Protection + Sprinkler System

All PDFs have been flattened (non-editable) per DOB submittal requirements.

Let me know if anything needs to be revised or if the DOB intake desk asks for the originals in a different order. Glad to support the next phase — please reach out when you're ready for the post-permit fire protection inspections and we'll get the inspection proposal moving."""


def docx_to_pdf(docx: Path, pdf: Path) -> Path:
    """Use Word COM to export a .docx to PDF, preserving embedded images
    (signatures, letterhead). FileFormat=17 = wdFormatPDF. ExportAsFixedFormat
    is the canonical Word-to-PDF API."""
    import win32com.client as win32
    word = win32.gencache.EnsureDispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(docx), ReadOnly=True)
        try:
            # ExportFormat 17 = wdExportFormatPDF
            doc.ExportAsFixedFormat(
                OutputFileName=str(pdf),
                ExportFormat=17,
                OpenAfterExport=False,
                OptimizeFor=0,        # wdExportOptimizeForPrint
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        finally:
            doc.Close(SaveChanges=False)
    finally:
        word.Quit()
    return pdf


def convert_remaining_docx() -> None:
    if not DOC4_PDF.exists():
        print(f"Converting {DOC4_DOCX.name} → PDF")
        docx_to_pdf(DOC4_DOCX, DOC4_PDF)
    if not DOC5_PDF.exists():
        print(f"Converting {DOC5_DOCX.name} → PDF")
        docx_to_pdf(DOC5_DOCX, DOC5_PDF)


def write_draft() -> Path:
    PENDING.mkdir(parents=True, exist_ok=True)
    lines = [
        f"**To:** Nery Soto <{TO_EMAIL}>",
        "**From:** admin@buildingcodeconsulting.com",
        "**CC:** ycao@buildingcodeconsulting.com",
        f"**Subject:** {SUBJECT}",
        "",
        "**Attachments (6):**",
    ]
    for p in ATTACHMENTS:
        lines.append(f"  - {p.name}  ({p.stat().st_size//1024} KB)" if p.exists() else f"  - !! MISSING: {p.name}")
    lines += ["", "---", "", BODY, ""]
    DRAFT_MD.write_text("\n".join(lines), encoding="utf-8")
    return DRAFT_MD


def verify_attachments() -> tuple[bool, list[str]]:
    """Self-review: every attachment exists and is non-trivial size."""
    issues = []
    for p in ATTACHMENTS:
        if not p.exists():
            issues.append(f"MISSING: {p.name}")
            continue
        sz = p.stat().st_size
        if sz < 5 * 1024:
            issues.append(f"SUSPICIOUSLY SMALL ({sz} B): {p.name}")
    return (len(issues) == 0), issues


def main(send: bool = False):
    convert_remaining_docx()
    ok, issues = verify_attachments()
    draft = write_draft()
    print(f"Draft: {draft}")
    print("Attachments:")
    for p in ATTACHMENTS:
        marker = "OK" if p.exists() else "MISSING"
        print(f"  [{marker}] {p.name}  ({p.stat().st_size//1024 if p.exists() else 0} KB)")
    if not ok:
        print("ISSUES FOUND - fix before sending:")
        for x in issues:
            print(f"  - {x}")
        sys.exit(1)
    if not send:
        print("---")
        print(f"Email content ready for Nery Soto. Please review '{draft}' and type 'Y' to send.")
        return
    # SEND
    from email_sender import send_from_admin_with_attachments
    print("---")
    print(f"Sending to {TO_EMAIL} (CC ycao@) ...")
    success, info = send_from_admin_with_attachments(
        to_email=TO_EMAIL,
        subject=SUBJECT,
        body_plain=BODY,
        attachment_paths=[str(p) for p in ATTACHMENTS],
    )
    print(f"  send result: success={success}  info={info}")
    if success:
        sent = draft.with_name(draft.stem + "-SENT.md")
        draft.rename(sent)
        print(f"  draft renamed -> {sent.name}")


if __name__ == "__main__":
    main(send=("--send" in sys.argv))


if __name__ == "__main__":
    main()
