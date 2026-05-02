"""
One-shot sender for Bucket A (5 followups) + Bucket B (1 fresh intro), 2026-04-27.
Reads each draft .md, parses headers, sends via email_sender.send_from_admin
with threading kwargs, then renames the draft to *-SENT.md and appends to a
local send log. Wrapped with active_operator lock per Phase 1 protocol.
"""

from __future__ import annotations

import csv
import os
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

DRAFT_FILES = [
    "Followup_Cecchini_JW_Marriott_20260427.md",
    "Followup_Matt_Benchmark_Insomnia_JoeJuice_20260427.md",
    "Followup_Tounkara_JW_Marriott_Restaurant_20260427.md",
    "Followup_Erdelyi_PWC_WIT_20260427.md",
    "Followup_Eric_Persaud_OakHill_Modular_20260427.md",
    "Intro_Senit_Hailemariam_Cyberknife_20260427.md",
]


def parse_draft(path: Path) -> dict:
    """Parse the markdown draft. Headers are listed before the first '---' divider line.
    Body is everything after that. Returns dict with to/subject/in_reply_to/references/body."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n---\s*\n", text, maxsplit=2)
    if len(parts) < 2:
        raise ValueError(f"Cannot find header/body divider in {path.name}")
    header_block = parts[0] + parts[1] if len(parts) >= 3 else parts[0]
    body = parts[-1].strip()

    def get(key: str) -> str | None:
        m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+)", header_block)
        if not m:
            return None
        v = m.group(1).strip()
        # strip backticks around message-ids
        v = v.strip("`").strip()
        return v or None

    to_field = get("To")
    if not to_field:
        raise ValueError(f"No To: in {path.name}")
    to_email = re.search(r"[\w\.\-+]+@[\w\.\-]+", to_field).group(0)

    subject = get("Subject")
    if not subject:
        raise ValueError(f"No Subject: in {path.name}")

    irt = get("In-Reply-To")
    if irt:
        irt = irt.strip("`")
    refs = get("References")
    if refs:
        refs = refs.strip("`")

    # Strip leading "(No In-Reply-To...)" parenthetical line from body if present
    body_lines = body.splitlines()
    while body_lines and body_lines[0].startswith("(No In-Reply-To"):
        body_lines.pop(0)
    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)
    body = "\n".join(body_lines)

    return {
        "draft_path": path,
        "to": to_email,
        "subject": subject,
        "in_reply_to": irt,
        "references": refs,
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
            print(f"[!] Missing draft: {p}")
            continue
        try:
            drafts.append(parse_draft(p))
        except Exception as e:
            print(f"[!] Parse error {p.name}: {e}")
    if len(drafts) != len(DRAFT_FILES):
        print(f"[!] Expected {len(DRAFT_FILES)} drafts, parsed {len(drafts)}. Aborting.")
        return 1

    print(f"\nReady to send {len(drafts)} emails. Each will be sent then the draft renamed to -SENT.md.")
    print()
    for d in drafts:
        print(f"  → {d['to']:50}  | {d['subject'][:80]}")

    print()
    sent = 0
    failed = 0
    for d in drafts:
        print(f"\n[SEND] {d['to']}  |  {d['subject'][:80]}")
        try:
            ok, msg = send_from_admin(
                to_email=d["to"],
                subject=d["subject"],
                body_plain=d["body"],
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
        time.sleep(2)  # gentle pacing — privateemail SMTP rate limit

    print(f"\n=== Done. Sent={sent}, Failed={failed} ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    with operator_lock("send_bucket_a_b_20260427.py"):
        sys.exit(main())
