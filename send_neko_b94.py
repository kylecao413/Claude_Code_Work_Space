"""Send Neko + B94 proposal emails (admin@, CC ycao@, PDF attached)."""
from email_sender import send_from_admin_with_attachment
from pathlib import Path

PROJECTS = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects")

EMAILS = [
    {
        "label": "Neko Health",
        "to": "jlopatin@sachse.net",
        "subject": "Third-Party Code Compliance Inspection Proposal – Neko Health, Anthem Row (Washington DC)",
        "attachment": PROJECTS / "Sachse Construction" / "Neko Health - Anthem Row - Washington DC" / "Neko Health - Anthem Row - Washington DC - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Jonathan,

Thank you for the opportunity to bid on the Neko Health — Anthem Row project at 700 K Street NW. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: flat rate of $350 per inspection visit covering Building, Mechanical, Electrical, Plumbing, and Fire Protection code compliance per the DC Third-Party Inspection program.

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The visit count shown in Exhibit C is our best estimate only — never a cap, never bundled, never billed upfront. If the job runs more or fewer visits, the invoice follows actual visits one-for-one.

We offer same-day or next-business-day inspection scheduling, including evenings and weekends at the same rate with no surcharge.

Happy to jump on a quick 5-minute call if it helps. Looking forward to supporting the team on this one.
""",
    },
    {
        "label": "B94 Breaker Repair",
        "to": "natasha.solis@desbuild.com",
        "subject": "Third-Party Code Compliance Inspection Proposal – Repair Faulty Circuit Breaker B94, JBAB",
        "attachment": PROJECTS / "Desbuild, Inc" / "Repair Faulty Circuit Breaker B94 at JBAB" / "Repair Faulty Circuit Breaker B94 at JBAB - Third Party Code Inspection Proposal from BCC.pdf",
        "body": """Hi Natasha,

Thank you for including BCC on the B94 faulty circuit breaker repair at JBAB. Please find attached our Third-Party Code Compliance Inspection Proposal from Building Code Consulting LLC (BCC).

Proposal summary: Electrical-only scope (new conduits, duct bank, breaker replacement and energization). Other disciplines are marked not applicable for this task order. Flat rate of $350 per inspection visit, estimated at 2 visits (rough-in + final).

Billing approach: invoices are issued per visit actually performed, at the flat per-visit rate. The 2-visit count is our best estimate — if scope changes or additional visits are needed, each is billed individually at the same rate. Never billed upfront, never capped by the estimate.

Same-day or next-business-day scheduling is available at no surcharge for evenings or weekends.

Happy to answer any questions on the proposal or scope.
""",
    },
]

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    for em in EMAILS:
        if not em["attachment"].exists():
            print(f"[SKIP] {em['label']}: attachment not found at {em['attachment']}")
            continue
        print(f"\n=== {em['label']} ===")
        print(f"To: {em['to']}")
        print(f"Subject: {em['subject']}")
        print(f"Attachment: {em['attachment'].name} ({em['attachment'].stat().st_size // 1024} KB)")
        print(f"Body:\n---\n{em['body']}---")
        if dry_run:
            print("[DRY RUN — not sending]")
            continue
        ok, msg = send_from_admin_with_attachment(
            to_email=em["to"],
            subject=em["subject"],
            body_plain=em["body"],
            attachment_path=str(em["attachment"]),
        )
        print(f"Result: {'SENT' if ok else 'FAILED'} — {msg}")
