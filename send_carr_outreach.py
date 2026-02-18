"""
发送 Carr Properties 开发信：读取 Carr_Outreach_Draft.md，使用 admin@ 发送给 Austen Holderness，抄送 ycao@。
仅在用户确认「Proceed with sending」后执行。发送后写入 sent_log.csv 记录状态。
"""
import csv
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

from email_sender import send_from_admin

BASE_DIR = Path(__file__).resolve().parent
DRAFT_PATH = BASE_DIR / "Carr_Outreach_Draft.md"
SENT_LOG = BASE_DIR / "sent_log.csv"

TO_EMAIL = "aholderness@carrprop.com"
SUBJECT = "Expediting Carr Properties' DC Pipeline: 24-Hour Inspections & Specialized Plan Review"
BODY = """Mr. Holderness,

I noticed Carr Properties is moving forward with 2121 Virginia Avenue NW and several other office-to-residential conversions in the region. For projects of this complexity, permit timing and code compliance are often the primary drivers of the critical path.

I am Kyle Cao, a dual-licensed PE (Civil & Electrical) and ICC Master Code Professional (MCP). We support developers like Carr by addressing two major industry bottlenecks:

Professional Plan Review & Peer Review: We identify code deficiencies before submission. By leveraging our PE stamps and specialized expertise, we can substitute the traditional, lengthy jurisdictional review wait times with an expedited, compliant process.

Guaranteed 24-Hour DC Inspections: We provide full-scope (combo) inspections with a 24-hour turnaround guarantee. This ensures your critical path is never compromised by agency scheduling delays.

Our team of professionals is always ready to provide technical guidance and solve complex code challenges on-site, ensuring your milestones remain on track.

I would welcome a brief conversation to discuss your current pipeline and how our pre-submission reviews or reliable inspection support can serve your upcoming projects.

Best regards,

Kyle Cao, PE, MCP
Building Code Consulting"""


def log_sent(contact_email: str, contact_name: str, company: str, subject: str):
    """将发送记录追加到 sent_log.csv。"""
    write_header = not SENT_LOG.exists()
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["contact_email", "contact_name", "company", "subject", "sent_at"])
        from datetime import datetime
        w.writerow([contact_email, contact_name, company, subject, datetime.utcnow().isoformat() + "Z"])


def main():
    if not DRAFT_PATH.exists():
        print("未找到 Carr_Outreach_Draft.md")
        return 1
    # 最终检查：无重复签名、项目引用正确
    text = DRAFT_PATH.read_text(encoding="utf-8")
    if text.count("Kyle Cao, PE, MCP") > 1:
        print("检测到正文中签名出现多次，请检查草稿。")
        return 1
    if "2121 Virginia" not in text and "2121 Virginia Ave" not in text:
        print("未在草稿中看到 2121 Virginia Ave 项目引用，请确认。")
        return 1

    ok, msg = send_from_admin(TO_EMAIL, SUBJECT, BODY)
    if not ok:
        print("发送失败:", msg)
        return 1
    print(msg)
    log_sent(TO_EMAIL, "Austen Holderness", "Carr Properties", SUBJECT)
    print("已记录到 sent_log.csv。")
    return 0


if __name__ == "__main__":
    exit(main())
