"""Resend 1300 Girard Street NW proposal from Gmail to Nicole."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_sender import send_from_gmail_with_attachment

TO = "nerdelyi@pwccompanies.com"
SUBJECT = "Re: Bids Due ASAP: 1300 Girard Street"

BODY = """Hi Nicole,

Thank you for the reminder. Please find attached our Third-Party Code Compliance Inspection proposal from Building Code Consulting LLC (BCC) for 1300 Girard Street NW.

We are a DC-licensed Third-Party Inspection Agency. Our team brings together licensed Professional Engineers across all major disciplines and multiple ICC Master Code Professionals (MCP). We handle Building, Mechanical, Electrical, Plumbing, and Fire Protection code inspections and serve as a hands-on technical resource for code compliance questions, providing professional guidance when issues arise.

We offer same-day or next-business-day inspection scheduling.

Billing is based on actual visits completed. The fee is a flat rate per visit actually performed, so you are never billed based on an upfront estimate.

Also, as a quick note, BCC also offers Third-Party Plan Review Services if needed on this or any future projects.

Please let us know if you have any questions. We look forward to working with PWC Companies on this project."""

PDF = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "Projects", "PWC Companies", "1300 Girard Street NW",
    "1300 Girard Street NW - Third Party Code Inspection Proposal from BCC.pdf",
)

if __name__ == "__main__":
    print(f"From:    caoyueno5@gmail.com")
    print(f"To:      {TO}")
    print(f"Subject: {SUBJECT}")
    print(f"PDF:     {os.path.basename(PDF)}")
    print(f"PDF exists: {os.path.isfile(PDF)}")
    print()
    print("--- Email Body ---")
    print(BODY)
    print("--- End ---")
    print()
    ans = input("Send from Gmail? (Y/n): ").strip()
    if ans.upper() in ("Y", "YES", ""):
        ok, msg = send_from_gmail_with_attachment(TO, SUBJECT, BODY, PDF)
        print(f"{'SUCCESS' if ok else 'FAILED'}: {msg}")
    else:
        print("Aborted.")
