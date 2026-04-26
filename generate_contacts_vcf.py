"""
从 bc_project_details.json + bc_bidboard_latest.json + sent_log.csv 合并出联系人列表，
生成 vCard 3.0 .vcf 文件。Kyle 可以直接导入 PrivateEmail 网页邮箱的 Contacts。

合并逻辑：
- bid board contact 字段（如 "Sandra Rodriguez"）优先于 detail 页的缩写（"SR"）
- BC detail 页提供 phone + project address
- sent_log.csv 提供历史联系人（company, name）
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _clean_company(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s*-\s*[A-Z][A-Za-z &\.,'/]+$", "", s).strip()


def _is_initials(s: str) -> bool:
    """判断是否只是 2-3 个大写字母的缩写（像 SR, JL, EP）。"""
    if not s:
        return True
    t = s.strip()
    return len(t) <= 3 and t.isalpha() and t.isupper()


def _vcard_escape(s: str) -> str:
    if not s:
        return ""
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _build_vcard(c: dict) -> str:
    """vCard 3.0, 兼容 PrivateEmail/Roundcube。"""
    full_name = c.get("name") or c.get("email").split("@")[0]
    # 尝试分 First / Last
    parts = full_name.split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{_vcard_escape(full_name)}",
        f"N:{_vcard_escape(last)};{_vcard_escape(first)};;;",
    ]
    if c.get("company"):
        lines.append(f"ORG:{_vcard_escape(c['company'])}")
    if c.get("email"):
        lines.append(f"EMAIL;TYPE=INTERNET;TYPE=WORK:{c['email']}")
    if c.get("phone"):
        lines.append(f"TEL;TYPE=WORK,VOICE:{c['phone']}")
    if c.get("proj_addr"):
        # Place project address in NOTE so Kyle knows source
        lines.append(f"NOTE:BCC — Project addr: {_vcard_escape(c['proj_addr'])}")
    else:
        lines.append(f"NOTE:BCC contact (imported {datetime.now():%Y-%m-%d})")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


def collect() -> list[dict]:
    merged: dict[str, dict] = {}

    # 1) bid board 列表的 contact 名是全名
    bb_path = BASE_DIR / "bc_bidboard_latest.json"
    bb_contact_by_oppid: dict[str, tuple[str, str, str]] = {}
    if bb_path.exists():
        for r in json.loads(bb_path.read_text(encoding="utf-8")):
            oid = r.get("opportunity_id") or ""
            c_name = r.get("contact") or ""
            c_client = r.get("client") or ""
            c_loc = r.get("location") or ""
            if oid and c_name:
                bb_contact_by_oppid.setdefault(oid, (c_name, c_client, c_loc))

    # 2) bc_project_details 提供 email / phone / full address
    det_path = BASE_DIR / "bc_project_details.json"
    if det_path.exists():
        for r in json.loads(det_path.read_text(encoding="utf-8")):
            em = (r.get("contact_email") or "").strip().lower()
            if not em:
                continue
            detail_name = r.get("contact_name") or ""
            oid = (r.get("_bidboard", {}) or {}).get("opportunity_id", "")
            bb = bb_contact_by_oppid.get(oid)
            # 若 detail 是缩写但 bid board 有全名，用 bid board 名
            name = detail_name
            if _is_initials(name) and bb:
                name = bb[0]
            company = _clean_company(r.get("client_company") or (bb[1] if bb else ""))
            phone = r.get("contact_phone") or ""
            addr = r.get("Location") or ""
            if em not in merged:
                merged[em] = {
                    "email": em, "name": name, "company": company,
                    "phone": phone, "proj_addr": addr, "source": "BC",
                }
            else:
                # 补齐缺字段
                mc = merged[em]
                if _is_initials(mc["name"]) and not _is_initials(name):
                    mc["name"] = name
                for k in ("company", "phone", "proj_addr"):
                    if not mc.get(k) and r.get(k):
                        mc[k] = r[k]

    # 3) sent_log.csv 老联系人
    log_path = BASE_DIR / "sent_log.csv"
    if log_path.exists():
        with open(log_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                em = (row.get("contact_email") or "").strip().lower()
                if not em or "@" not in em:
                    continue
                if em in merged:
                    # 可能补名字
                    mc = merged[em]
                    if _is_initials(mc.get("name", "")) and row.get("contact_name"):
                        mc["name"] = row["contact_name"]
                    if not mc.get("company") and row.get("company"):
                        mc["company"] = row["company"]
                    continue
                merged[em] = {
                    "email": em,
                    "name": row.get("contact_name") or "",
                    "company": row.get("company") or "",
                    "phone": "",
                    "proj_addr": "",
                    "source": "sent_log",
                }

    return list(merged.values())


def main():
    contacts = collect()
    # Exclude blocked domains (dc.gov etc — per memory)
    blocked_domains = ["dc.gov", "wmata.com"]
    contacts = [c for c in contacts if not any(c["email"].endswith("@" + d) for d in blocked_domains)]

    bc_count = sum(1 for c in contacts if c["source"] == "BC")
    log_count = sum(1 for c in contacts if c["source"] == "sent_log")

    # 生成 .vcf
    out_all = BASE_DIR / f"BCC_contacts_all_{datetime.now():%Y%m%d}.vcf"
    out_new = BASE_DIR / f"BCC_contacts_BC_new_{datetime.now():%Y%m%d}.vcf"

    all_vcf = "\r\n".join(_build_vcard(c) for c in contacts) + "\r\n"
    new_vcf = "\r\n".join(_build_vcard(c) for c in contacts if c["source"] == "BC") + "\r\n"

    out_all.write_text(all_vcf, encoding="utf-8")
    out_new.write_text(new_vcf, encoding="utf-8")

    print(f"Wrote:")
    print(f"  {out_all.name}   ({len(contacts)} contacts total)")
    print(f"  {out_new.name}   ({bc_count} new BC contacts only)")
    print()
    print(f"合计: {len(contacts)} (BC {bc_count} + sent_log {log_count})")
    # 过滤后的 BC 新联系人预览
    print("\nBC 新联系人（可导入到 PrivateEmail）：")
    for c in contacts:
        if c["source"] != "BC":
            continue
        print(f"  {c['name']:<25} {c['email']:<40} {c['company'][:28]:<28} {c['phone']}")


if __name__ == "__main__":
    main()
