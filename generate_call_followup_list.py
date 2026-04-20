"""
generate_call_followup_list.py — 生成 Call_Follow_Up_List.md 单一 living doc。

合并数据源（按 email 匹配）：
1. VCF 文件（BCC_contacts_*.vcf）— 电话 + 项目地址
2. phone_log.csv — 当前通话状态 + 上次 call 日期 + notes
3. sent_log.csv — 邮件历史（发了几封，最后发送日期，是否回复）

输出: repo 根目录 Call_Follow_Up_List.md，分区：
- HOT (有电话 + 发过邮件无回复) — 立刻打
- NEEDS PHONE (发过邮件无电话) — 先找电话
- CALLED (上次 call 有记录) — 下一步跟进
- REPLIED (对方已回复) — 上下文参考

每个联系人 card 包含：姓名/公司/电话/email/项目/我们服务/邮件历史/个性化 call script。

用法: python generate_call_followup_list.py
更新: Kyle 报告"call 了 X"后，我手动改 phone_log.csv 对应行的 last_call_date/call_status/notes 再重跑这脚本。
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "Call_Follow_Up_List.md"


# ============================================================================
# DATA LOADING
# ============================================================================
def parse_vcf(vcf_path: Path) -> list:
    """解析 vCard 3.0 文件 → [{name, company, email, phone, project_addr}]。"""
    if not vcf_path.exists():
        return []
    text = vcf_path.read_text(encoding="utf-8", errors="replace")
    cards = []
    for block in text.split("BEGIN:VCARD"):
        if "END:VCARD" not in block:
            continue
        card = {"name": "", "company": "", "email": "", "phone": "", "project_addr": ""}
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("FN:"):
                card["name"] = line[3:].strip()
            elif line.startswith("ORG:"):
                # VCF escapes: \, -> , and \\ -> \
                card["company"] = line[4:].replace("\\,", ",").replace("\\\\", "\\").strip()
            elif line.startswith("EMAIL"):
                m = re.search(r":(\S+@\S+)", line)
                if m:
                    card["email"] = m.group(1).strip().lower()
            elif line.startswith("TEL"):
                m = re.search(r":([+\d\s\-().ext]+)", line)
                if m:
                    card["phone"] = m.group(1).strip()
            elif line.startswith("NOTE:"):
                note = line[5:].replace("\\,", ",").replace("\\n", " ").strip()
                m = re.search(r"Project addr:\s*(.+)", note)
                if m:
                    card["project_addr"] = m.group(1).strip()
        if card["email"] or card["name"]:
            cards.append(card)
    return cards


def load_phone_log() -> dict:
    """email(lower) → phone_log row。"""
    path = BASE_DIR / "phone_log.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            em = (row.get("email") or "").strip().lower()
            if em:
                out[em] = row
    return out


def load_sent_log() -> dict:
    """email(lower) → {sent_count, last_sent, replied, subject, project}."""
    path = BASE_DIR / "sent_log.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            em = (row.get("contact_email") or "").strip().lower()
            if not em:
                continue
            sent_at = (row.get("sent_at") or "").strip()
            followup_at = (row.get("followup_sent_at") or "").strip()
            sent_count = (1 if sent_at else 0) + (1 if followup_at else 0)
            last_sent = max(filter(None, [sent_at, followup_at]), default="")
            out[em] = {
                "sent_count": sent_count,
                "last_sent": last_sent,
                "replied": (row.get("replied") or "").strip().lower() in ("yes", "true", "1", "y"),
                "subject": (row.get("subject") or "").strip(),
                "project": (row.get("project") or "").strip(),
                "company": (row.get("company") or "").strip(),
                "contact_name": (row.get("contact_name") or "").strip(),
            }
    return out


def merge_contacts(vcf_cards, phone_log, sent_log) -> list:
    """按 email 合并所有源 → unified contact list。"""
    merged = {}  # key: email (lower)

    # 1. VCF 优先（有 phone 和 project_addr）
    for c in vcf_cards:
        em = c.get("email", "")
        if em:
            merged[em] = {
                "email": em,
                "name": c.get("name", ""),
                "company": c.get("company", ""),
                "phone": c.get("phone", ""),
                "project_addr": c.get("project_addr", ""),
                "project": "",  # 从 sent_log 或 phone_log 补
                "call_status": "",
                "last_call": "",
                "notes": "",
                "sent_count": 0,
                "last_sent": "",
                "replied": False,
                "subject": "",
            }

    # 2. phone_log 合并（call 状态）
    for em, row in phone_log.items():
        if em not in merged:
            merged[em] = {
                "email": em,
                "name": row.get("contact_name", ""),
                "company": row.get("company", ""),
                "phone": row.get("phone", "").strip(),
                "project_addr": "",
                "project": row.get("project", ""),
                "call_status": "",
                "last_call": "",
                "notes": "",
                "sent_count": 0,
                "last_sent": "",
                "replied": False,
                "subject": "",
            }
        c = merged[em]
        # phone_log 的 phone 如果 VCF 没填就用
        if not c["phone"] and row.get("phone", "").strip():
            c["phone"] = row["phone"].strip()
        if not c["project"] and row.get("project", "").strip():
            c["project"] = row["project"].strip()
        c["call_status"] = row.get("call_status", "").strip()
        c["last_call"] = row.get("last_call_date", "").strip()
        c["notes"] = row.get("notes", "").strip()

    # 3. sent_log 合并（email 历史）
    for em, s in sent_log.items():
        if em not in merged:
            merged[em] = {
                "email": em,
                "name": s.get("contact_name", ""),
                "company": s.get("company", ""),
                "phone": "",
                "project_addr": "",
                "project": s.get("project", ""),
                "call_status": "",
                "last_call": "",
                "notes": "",
                "sent_count": 0,
                "last_sent": "",
                "replied": False,
                "subject": "",
            }
        c = merged[em]
        if not c["name"]:
            c["name"] = s.get("contact_name", "")
        if not c["company"]:
            c["company"] = s.get("company", "")
        if not c["project"]:
            c["project"] = s.get("project", "")
        c["sent_count"] = s.get("sent_count", 0)
        c["last_sent"] = s.get("last_sent", "")
        c["replied"] = s.get("replied", False)
        c["subject"] = s.get("subject", "")

    return list(merged.values())


# ============================================================================
# CLASSIFICATION
# ============================================================================
def classify(c: dict) -> str:
    """hot_email / hot_bc_bid / needs_phone / called / replied / cold。"""
    if c.get("replied"):
        return "replied"
    if c.get("last_call") and c.get("last_call").strip():
        return "called"
    if c.get("phone") and c.get("sent_count", 0) >= 1:
        return "hot_email"  # 发过冷邮件 + 有电话，follow up on email
    if c.get("phone"):
        return "hot_bc_bid"  # 有电话但没冷邮件 — BC 投标 contact，follow up on proposal
    if c.get("sent_count", 0) >= 1:
        return "needs_phone"
    return "cold"


def days_since(date_str: str) -> int | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            d = datetime.strptime(date_str.strip(), fmt).date()
            return (date.today() - d).days
        except ValueError:
            continue
    return None


# ============================================================================
# CALL SCRIPT GENERATION
# ============================================================================
def first_name(full_name: str) -> str:
    parts = (full_name or "").strip().split()
    return parts[0] if parts else "there"


def infer_service(company: str) -> str:
    """根据公司名推断 pitch：GC → inspection only; 其他 → inspection + plan review 备选。"""
    c = (company or "").lower()
    gc_keywords = ["construction", "builders", "contractor", "build", "general", "gc"]
    if any(k in c for k in gc_keywords):
        return "DC Third-Party Combo Inspection (flat $350/visit, same/next-day scheduling)"
    return "DC Third-Party Combo Inspection + Plan Review (flat $350/visit for inspection)"


def short_project(project: str) -> str:
    """项目名截短到前 ~40 字符，去掉冗余后缀。"""
    p = (project or "").strip()
    if not p:
        return "your DC project"
    # 去掉标点结尾
    p = re.sub(r"\s+", " ", p)
    if len(p) > 45:
        p = p[:42] + "..."
    return p


def render_call_script(c: dict) -> list:
    """casual marketing-guy 风格 script，根据 state 切换开场。"""
    fn = first_name(c["name"])
    proj = short_project(c.get("project", ""))
    proj_addr = c.get("project_addr", "").strip()
    service = infer_service(c.get("company", ""))
    sent_count = c.get("sent_count", 0)
    days = days_since(c.get("last_sent", ""))
    state = classify(c)

    # 引用邮件的自然说法
    if sent_count >= 2:
        email_ref = "I actually sent you a couple notes — latest one"
        if days and days < 14:
            email_ref += f" about {days} days ago"
        else:
            email_ref += " a little while back"
    elif sent_count == 1:
        if days and days < 7:
            email_ref = f"I sent you a quick note {days} days ago"
        elif days and days < 21:
            email_ref = "I sent you a note a couple weeks back"
        else:
            email_ref = "I sent you a note earlier this month"
    else:
        email_ref = ""

    lines = [
        "**📞 Call Script** _(casual, 15s opening)_",
        "",
        "**Opening:**",
        f'> "Hey {fn}, this is Kyle from Building Code Consulting — got 30 seconds? ',
    ]
    if state == "hot_bc_bid":
        # BC 投标 follow-up — 不提 cold email，提 proposal
        addr_short = proj_addr.replace(", United States of America", "").strip()
        has_project_name = c.get("project", "").strip() and c.get("project", "").strip() != ""
        if has_project_name and addr_short:
            where_str = f"the {proj} project at {addr_short}"
        elif has_project_name:
            where_str = f"the {proj} project"
        elif addr_short:
            where_str = f"the project at {addr_short}"
        else:
            where_str = "the project"
        lines.append(
            f'> We submitted a code inspection proposal for {where_str} '
            f'a little while back — just circling back to see if you\'re close to a decision '
            f'on that one, or if there\'s anything I can clarify."'
        )
    elif sent_count >= 1:
        lines.append(
            f'> {email_ref} about {proj} — just wanted to close the loop and see '
            f'if code inspection support is still on your radar for that one."'
        )
    else:
        lines.append(
            f'> Reaching out because we do DC third-party code inspections and your '
            f'name came up in connection with {proj}. Quick one — is inspection support '
            f'something you\'re looking at?"'
        )

    lines += [
        "",
        "**If interested:**",
        f'> "Cool. Real quick: we do {service.split(" (")[0]}. '
        f'Flat $350/visit, no upfront estimate — billed per visit actually done. '
        f'Same or next-business-day scheduling. I can shoot you a one-pager, '
        f'or set up a 10-min call with our PE to walk through specifics. '
        f'Which works better?"',
        "",
        "**If busy / bad time:**",
        f'> "No worries — totally get it. I\'ll shoot over a quick summary by email, '
        f'you can look whenever. Have a good one, {fn}."',
        "",
        "**Key talking points if asked:**",
        "- BCC: PE + ICC Master Code Professional (MCP) team, covers all major disciplines",
        "- Same or next business day inspection scheduling",
        "- Flat $350/visit, billed per visit actually performed (no upfront estimation)",
        "- Also do third-party plan review (mention only if they're owner/architect, not GC)",
        "- Territory: DC, Northern VA, PG County, Montgomery County for inspections",
    ]
    return lines


# ============================================================================
# MARKDOWN RENDERING
# ============================================================================
def render_contact_card(c: dict) -> list:
    service = infer_service(c.get("company", ""))
    sent_count = c.get("sent_count", 0)
    last_sent = c.get("last_sent", "")
    days = days_since(last_sent)
    email_hist_line = (
        f"{sent_count} email(s), last {last_sent[:10] or '?'} "
        f"({days}d ago)" if days is not None else
        f"{sent_count} email(s), last {last_sent[:10] or '(none)'}"
    )
    reply_line = "✅ REPLIED" if c.get("replied") else "❌ no reply"
    phone_line = c.get("phone") or "_(NOT IN TRACKER — check LinkedIn / company site)_"

    lines = [
        f"### {c['name'] or '(unknown name)'} — {c['company'] or '(unknown company)'}",
        f"- **Email**: `{c['email']}`  _(sent from: admin@buildingcodeconsulting.com unless sent_log says otherwise)_",
        f"- **Phone**: {phone_line}",
        f"- **Title/Role**: _(not in tracker — check LinkedIn)_",
        f"- **Project**: {c.get('project') or '_(unknown)_'}",
    ]
    if c.get("project_addr"):
        lines.append(f"- **Project Addr**: {c['project_addr']}")
    lines.append(f"- **Service we pitch**: {service}")
    lines.append(f"- **Email history**: {email_hist_line} — {reply_line}")
    if c.get("subject"):
        lines.append(f"- **Last subject**: _{c['subject'][:80]}_")
    if c.get("last_call"):
        lines.append(f"- **Last call**: {c['last_call']} — status: {c.get('call_status', '?')}")
    if c.get("notes"):
        lines.append(f"- **Notes**: {c['notes']}")
    lines.append("")
    lines.extend(render_call_script(c))
    lines.append("")
    lines.append(
        "**✏️ Post-call update** _(告诉 Claude: 我 call 了 X, 结果 Y, 下一步 Z)_ — Claude 会改 phone_log.csv"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def render_markdown(contacts: list) -> str:
    # 分类
    hot_email = [c for c in contacts if classify(c) == "hot_email"]
    hot_bc_bid = [c for c in contacts if classify(c) == "hot_bc_bid"]
    needs_phone = [c for c in contacts if classify(c) == "needs_phone"]
    called = [c for c in contacts if classify(c) == "called"]
    replied = [c for c in contacts if classify(c) == "replied"]

    hot_email.sort(key=lambda c: c.get("last_sent", ""), reverse=True)
    needs_phone.sort(key=lambda c: c.get("last_sent", ""), reverse=True)
    hot_bc_bid.sort(key=lambda c: c.get("company", ""))

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_hot = len(hot_email) + len(hot_bc_bid)
    out = [
        "# BCC Cold-Call Follow-Up List",
        "",
        f"**Generated**: {ts}  ",
        f"**Source**: `phone_log.csv` + `sent_log.csv` + `BCC_contacts_all_*.vcf`",
        "",
        "## Summary",
        f"- 🔥 **HOT — Call Now**：**{total_hot}** 个 (email follow-up: {len(hot_email)}, BC bid follow-up: {len(hot_bc_bid)})",
        f"- 📱 **NEEDS PHONE** (发过邮件无电话)：**{len(needs_phone)}** 个 — 先找电话",
        f"- ☎️ **CALLED** (上次 call 有记录)：{len(called)} 个",
        f"- ✅ **REPLIED** (对方已回复)：{len(replied)} 个",
        "",
        "_脚本风格：casual marketing-guy，≤15s opening，引用发过的邮件/投标，不 dump credentials。_",
        "",
        "---",
        "",
    ]

    if hot_email:
        out.append("## 🔥 HOT — Cold Email Follow-Up Call (有电话 + 发过邮件无回复)")
        out.append("")
        for c in hot_email:
            out.extend(render_contact_card(c))

    if hot_bc_bid:
        out.append("## 🔥 HOT — BC Bid Follow-Up Call (我们提交了 proposal 的 BC contact)")
        out.append("")
        for c in hot_bc_bid:
            out.extend(render_contact_card(c))

    if needs_phone:
        out.append("## 📱 NEEDS PHONE HUNT — Find phone first, then add to HOT")
        out.append("")
        out.append(
            f"_以下 {len(needs_phone)} 人发了邮件但 tracker 没电话。_  \n"
            "_建议找电话的顺序：1) LinkedIn → 2) 公司官网 Contact 页 → 3) Apollo.io 免费查询_"
        )
        out.append("")
        for c in needs_phone:
            out.extend(render_contact_card(c))

    if called:
        out.append("## ☎️ CALLED ALREADY — Next Step Follow-Up")
        out.append("")
        for c in called:
            out.extend(render_contact_card(c))

    if replied:
        out.append("## ✅ REPLIED — Context Reference")
        out.append("")
        for c in replied:
            out.extend(render_contact_card(c))

    return "\n".join(out)


# ============================================================================
# MAIN
# ============================================================================
def main():
    # 找所有 VCF
    vcf_files = sorted(BASE_DIR.glob("BCC_contacts_*.vcf"), reverse=True)
    vcf_cards = []
    for vcf in vcf_files:
        vcf_cards.extend(parse_vcf(vcf))
    # 按 email dedupe（同一 email 多个 vcf 保最后一个 — 最新）
    vcf_dedup = {}
    for c in vcf_cards:
        em = c.get("email", "")
        if em:
            vcf_dedup[em] = c
    vcf_cards = list(vcf_dedup.values())
    print(f"VCF 里解析出 {len(vcf_cards)} 个 contact (去重后), "
          f"其中 {sum(1 for c in vcf_cards if c.get('phone'))} 有电话")

    phone_log = load_phone_log()
    print(f"phone_log.csv: {len(phone_log)} rows")

    sent_log = load_sent_log()
    print(f"sent_log.csv: {len(sent_log)} rows")

    contacts = merge_contacts(vcf_cards, phone_log, sent_log)
    print(f"合并后: {len(contacts)} unique contacts (by email)")

    md = render_markdown(contacts)
    OUTPUT_PATH.write_text(md, encoding="utf-8")
    print(f"\n写入: {OUTPUT_PATH}")
    print(f"总字节: {len(md):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
