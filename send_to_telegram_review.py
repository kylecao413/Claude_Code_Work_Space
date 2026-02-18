"""
send_to_telegram_review.py
把最终版 email 草稿(.md) 和提案 PDF 发到 Telegram，供手机端审阅。
同时清理 Pending_Approval/Outbound 里的旧版草稿。
"""
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import requests

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_IDS_RAW = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
if not BOT_TOKEN or not CHAT_IDS_RAW:
    print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_CHAT_IDS missing from .env")
    sys.exit(1)
CHAT_ID = CHAT_IDS_RAW.split(",")[0].strip()

OUTBOUND = ROOT / "Pending_Approval" / "Outbound"
PROJECTS = ROOT.parent / "Projects"

# ── Files to DELETE (old drafts) ──────────────────────────────────────────────
OLD_DRAFTS = [
    "20_F_Street_NW_Suite_550_Proposal_Draft.md",
    "BC_Proposal_20_F_Street_Northwest,_Suite_550_Tenant_Renovation_Draft.md",
    "BC_Proposal_St._Joseph's_on_Capitol_Hill_–_Phase_I_Draft.md",
    "Proposal_Draft_20_F_Street_Northwest,_Suite_550_Tenant_Renovation.md",
    # older email drafts replaced by timestamped READY files
    "Email_20_F_Street_NW_Suite550_READY.md",
    "Email_St_Josephs_Capitol_Hill_READY.md",
]

# ── Final email content for both projects ─────────────────────────────────────
TS = datetime.now().strftime("%Y%m%d_%H%M")

EMAILS = [
    {
        "slug": "20F_Street_NW_Suite550",
        "to": "Angel Colon <acolon@hbwconstruction.com>",
        # Cold outreach: no "Proposal" in subject
        "subject": "Third-Party Inspection Services for 20 F St NW Suite 550 | Building Code Consulting LLC",
        "body": """\
Hi Angel,

I came across the 20 F Street NW, Suite 550 Tenant Renovation project and wanted to take a moment to introduce Building Code Consulting LLC (BCC) as a potential resource for your Third-Party Inspection needs.

BCC is a DC-based engineering firm focused exclusively on Washington, D.C. Third-Party Code Compliance Inspections. A few reasons HBW Construction may find us a strong fit for this project:

Multi-Discipline Expertise: Our team holds PE licenses (Civil and Electrical) and ICC Master Code Professional (MCP) certifications. We handle Building, Mechanical, Electrical, Plumbing, and Fire inspections and resolve technical code questions on-site to prevent delays.

Responsive Scheduling: We offer same-day or next-business-day inspection availability to keep your project milestones on track.

Fair, Visit-Based Billing: We bill strictly based on actual visits completed — never based on an upfront estimate. If your project wraps up in fewer inspections than projected, you pay only for what was done.

We are not submitting a formal proposal at this stage, but if you are still finalizing your inspection vendor list for this project, we would welcome the opportunity to provide a competitive quote.

Are you open to a quick 5-minute call or a brief capability overview?""",
        # Cold outreach: no PDF attachment
        "pdf": None,
    },
    {
        "slug": "St_Josephs_Capitol_Hill",
        "to": "Alex Pauley <apauley@kellerbrothers.com>",
        # Cold outreach: no "Proposal" in subject
        "subject": "Third-Party Inspection Services for St. Joseph's on Capitol Hill | Building Code Consulting LLC",
        "body": """\
Hi Alex,

I noticed that Keller Brothers is working on the St. Joseph's on Capitol Hill – Phase I project and wanted to briefly introduce Building Code Consulting LLC (BCC) as a potential resource for your Third-Party Inspection needs.

BCC is a DC-based engineering firm focused exclusively on Washington, D.C. Third-Party Code Compliance Inspections. A few reasons Keller Brothers may find us a strong fit for this project:

Multi-Discipline Coverage: Our team holds PE licenses (Civil and Electrical) and ICC Master Code Professional (MCP) certifications. We handle Building, Mechanical, Electrical, Plumbing, and Fire inspections under one roof and resolve technical disputes on-site to prevent unnecessary hold-ups.

Responsive Turnaround: We offer same-day or next-business-day scheduling to help protect your critical milestones — especially important for a project with historic components like this one.

Fair, Visit-Based Billing: We bill based on actual visits completed. You are never charged based on an upfront estimate. If inspections wrap up faster than projected, you pay only for what was done.

We are not submitting a formal proposal at this stage, but if you are still looking at inspection vendor options for this project, we would be happy to provide a competitive quote.

Are you open to a quick 5-minute call or a brief capability overview?""",
        # Cold outreach: no PDF attachment
        "pdf": None,
    },
]

# NOTE: These are cold outreach emails — no PDF attachments.
# If a client responds and requests a formal proposal, use send_proposals.py instead.


# ── Telegram helpers ──────────────────────────────────────────────────────────
def tg_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
    for chunk in chunks:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=15)
        if not r.ok:
            print(f"  Telegram message error: {r.status_code} {r.text}")
            return False
    return True


def tg_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        r = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption},
                          files={"document": (os.path.basename(file_path), f)}, timeout=60)
    if not r.ok:
        print(f"  Telegram document error: {r.status_code} {r.text}")
        return False
    return True


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # 1. Clean up old drafts
    print("── Step 1: Cleaning up old drafts ──")
    for name in OLD_DRAFTS:
        p = OUTBOUND / name
        if p.exists():
            p.unlink()
            print(f"  Deleted: {name}")
        else:
            print(f"  (not found, skip): {name}")

    # 2. Write timestamped READY files
    print("\n── Step 2: Writing timestamped email drafts ──")
    ready_files = []
    for em in EMAILS:
        fname = f"Email_{em['slug']}_{TS}.md"
        fpath = OUTBOUND / fname
        content = f"""# Email Draft — {em['slug'].replace('_', ' ')}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ← LATEST VERSION

**TO:** {em['to']}
**CC:** ycao@buildingcodeconsulting.com (auto)
**FROM:** admin@buildingcodeconsulting.com
**SUBJECT:** {em['subject']}

---

{em['body']}
"""
        fpath.write_text(content, encoding="utf-8")
        print(f"  Saved: {fname}")
        ready_files.append((fpath, em))

    # 3. Send to Telegram
    print("\n── Step 3: Sending to Telegram ──")
    header = (
        f"📋 *BCC Proposal Emails — Final Review*\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"两封提案邮件草稿 + PDF 如下，确认后回复 *Y* 让 Claude 发送。"
    )
    tg_message(header)

    for fpath, em in ready_files:
        # Send email body as text
        tg_text = (
            f"📧 *Email Draft — {em['slug'].replace('_', ' ')}*\n\n"
            f"*TO:* {em['to']}\n"
            f"*Subject:* {em['subject']}\n\n"
            f"---\n\n{em['body']}"
        )
        tg_message(tg_text)

        # Send .md file
        tg_document(fpath, caption=f"Email draft (.md): {fpath.name}")
        print(f"  Sent email draft: {fpath.name}")

        # Send PDF
        pdf = em["pdf"]
        if pdf and Path(pdf).is_file():
            tg_document(pdf, caption=f"Proposal PDF: {Path(pdf).name}")
            print(f"  Sent PDF: {Path(pdf).name}")
        else:
            print(f"  WARNING: PDF not found — {pdf}")

    tg_message("✅ 全部发送完毕。请审阅后回复 *Y* 确认发送，或告知修改意见。")
    print("\nDone.")


if __name__ == "__main__":
    main()
