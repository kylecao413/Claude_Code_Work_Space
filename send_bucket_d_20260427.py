"""
Sender for Bucket D (8 BC proposal followups, ≥5 weeks stale), 2026-04-27 PM.
Same pattern as send_bucket_a_b_20260427.py — parses CC for additional recipients.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from email_sender import send_from_admin  # noqa: E402
from core_tools.active_operator import operator_lock  # noqa: E402

OUTBOUND = ROOT / "Pending_Approval" / "Outbound"
SEND_LOG = ROOT / "bcc_proposal_sent_log.csv"
YCAO_AUTO = "ycao@buildingcodeconsulting.com"

DRAFT_FILES = [
    "Followup_Bmiller_Sachse_Rivian_20260427.md",
    "Followup_Tplum_Winmar_3050K_20260427.md",
    "Followup_Jlauer_HBW_Kolmac_20260427.md",
    "Followup_Tliang_Doyle_EagleBank_20260427.md",
    "Followup_Melissae_Victor_4900Georgia_20260427.md",
    "Followup_Agross_1154_4th_6024_8th_20260427.md",
    "Followup_Jwilliams_HBW_Endometriosis_20260427.md",
    "Followup_SEI_1425RhodeIsland_20260427.md",
]


def parse_draft(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n---\s*\n", text, maxsplit=2)
    if len(parts) < 2:
        raise ValueError(f"No header/body divider in {path.name}")
    header = parts[0] + ("\n" + parts[1] if len(parts) >= 3 else "")
    body = parts[-1].strip()

    def get(key: str) -> str | None:
        m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+)", header)
        return m.group(1).strip().strip("`") if m else None

    to_field = get("To")
    cc_field = get("CC")
    subject = get("Subject")
    irt = get("In-Reply-To")
    refs = get("References")
    if not (to_field and subject):
        raise ValueError(f"Missing To/Subject in {path.name}")

    to_email = re.search(r"[\w\.\-+]+@[\w\.\-]+", to_field).group(0)

    # Extract additional CCs (everything except ycao@ auto)
    extra_cc = []
    if cc_field:
        for e in re.findall(r"[\w\.\-+]+@[\w\.\-]+", cc_field):
            if e.lower() != YCAO_AUTO and e.lower() != to_email.lower():
                extra_cc.append(e)

    return {
        "draft_path": path,
        "to": to_email,
        "extra_cc": extra_cc,
        "subject": subject,
        "in_reply_to": irt.strip("`") if irt else None,
        "references": refs.strip("`") if refs else None,
        "body": body,
    }


def append_sent_log(d: dict, ok: bool, msg: str) -> None:
    is_new = not SEND_LOG.exists()
    with open(SEND_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["sent_at", "to", "subject", "in_reply_to", "draft", "ok", "message"])
        w.writerow([
            datetime.now(timezone.utc).isoformat(),
            d["to"], d["subject"], d.get("in_reply_to") or "",
            d["draft_path"].name, "Y" if ok else "N", msg[:200],
        ])


def main():
    drafts = []
    for fn in DRAFT_FILES:
        p = OUTBOUND / fn
        if not p.is_file():
            print(f"[!] Missing: {p}")
            continue
        try:
            drafts.append(parse_draft(p))
        except Exception as e:
            print(f"[!] Parse {p.name}: {e}")
    if len(drafts) != len(DRAFT_FILES):
        print(f"[!] Expected {len(DRAFT_FILES)}, parsed {len(drafts)}. Aborting.")
        return 1

    print(f"\nReady to send {len(drafts)} emails:\n")
    for d in drafts:
        cc_note = f"  +CC: {','.join(d['extra_cc'])}" if d["extra_cc"] else ""
        print(f"  → {d['to']:40} | {d['subject'][:75]}{cc_note}")
    print()

    sent = 0
    failed = 0
    for d in drafts:
        cc_str = " ".join(d["extra_cc"]) if d["extra_cc"] else None
        print(f"\n[SEND] {d['to']}  |  {d['subject'][:80]}")
        try:
            ok, msg = send_from_admin(
                to_email=d["to"],
                subject=d["subject"],
                body_plain=d["body"],
                cc=cc_str,
                in_reply_to=d.get("in_reply_to"),
                references=d.get("references"),
            )
        except Exception as e:
            ok, msg = False, f"Exception: {e}"
        print(f"   result: {'OK' if ok else 'FAIL'} — {msg}")
        append_sent_log(d, ok, msg)
        if ok:
            sent += 1
            new_name = d["draft_path"].with_name(d["draft_path"].stem + "-SENT.md")
            d["draft_path"].rename(new_name)
            print(f"   renamed → {new_name.name}")
        else:
            failed += 1
        time.sleep(2)

    print(f"\n=== Done. Sent={sent}, Failed={failed} ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    with operator_lock("send_bucket_d_20260427.py"):
        sys.exit(main())
