"""
send_cw_followups.py — Multi-touch follow-up sender for CW cold outreach.

3-touch follow-up sequence (in addition to the initial cold email = Touch 0):
  Touch 1 — Day 4   : short bump ("wanted to make sure this reached you")
  Touch 2 — Day 12  : value-add ("here's what's different about BCC")
  Touch 3 — Day 24  : break-up ("should I close the loop?")

Which touch to send is determined by the followup_count column in sent_log.csv
(0 = initial only, 1 = touch 1 sent, 2 = touch 2 sent, 3 = final).

Excludes:
  - DC Government contacts (§ 0-H)
  - Contacts who replied (replied=1 in sent_log)
  - Contacts already at touch 3 (break-up already sent)
  - Contacts whose next-touch window hasn't arrived yet

Usage:
    python send_cw_followups.py                       # Preview due follow-ups
    python send_cw_followups.py --dry-run             # Show full bodies
    python send_cw_followups.py --send                # Send with Y confirmation
    python send_cw_followups.py --send --touch 1      # Only send touch 1
    python send_cw_followups.py --send --limit 20     # Cap at 20 sends
    python send_cw_followups.py --send --sender admin # Only admin@
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from email_sender import (
    send_from_admin, send_from_ycao,
)

BASE_DIR = Path(__file__).resolve().parent
SENT_LOG = BASE_DIR / "sent_log.csv"

# ── DC Government exclusion (§ 0-H) ──────────────────────────────────────────
_GOV_DOMAINS = {"dc.gov", "wmata.com"}
_GOV_KEYWORDS = [
    "district of columbia", "dmped", "office of the deputy mayor",
    "department of general services", "department of buildings",
    "dc public schools", "dcps", "dc housing authority", "dcha", "wmata",
    "events d.c.", "eventsdc",
]


def _is_gov(email: str, company: str) -> bool:
    domain = email.lower().split("@")[-1]
    if domain in _GOV_DOMAINS:
        return True
    return any(kw in company.lower() for kw in _GOV_KEYWORDS)


# ── Replied detection ─────────────────────────────────────────────────────────
# The sent_log CSV has a misaligned "replied" column — values like
# "admin@buildingcodeconsulting.com" are actually sent_from, not replies.
# Only "1" in the replied column means an actual reply.
def _is_replied(replied_val: str) -> bool:
    v = (replied_val or "").strip()
    return v == "1"


# ── Email body generators ────────────────────────────────────────────────────
def _first_name(full_name: str) -> str:
    parts = (full_name or "").strip().split()
    return parts[0] if parts else ""


# ── Touch categorization ─────────────────────────────────────────────────────
# target_kind: "architect" (plan-review only), "gc" (TPI only), "owner_pr" (PR+TPI),
# "owner_tpi" (TPI lead with PR mention), "generic" (fallback)
def _infer_target_kind(subject: str, company: str) -> str:
    s = (subject or "").lower()
    c = (company or "").lower()
    if "plan review for" in s or "architects" in c or "architecture" in c or "design" in c and "construction" not in c:
        return "architect"
    if "plan review" in s and "tpi" in s:
        return "owner_pr"
    if "tpi inspector for" in s or ("inspection" in s and "plan review" not in s):
        return "gc"
    if "plan review" in s:
        return "owner_pr"
    return "generic"


# ── Touch 1 (Day 4): short bump ──────────────────────────────────────────────
def _touch1_body(first: str, company: str, project: str, kind: str) -> str:
    salutation = f"Hi {first}," if first else "Hi,"
    proj_ref = f"on {project}" if project else f"on your DC projects"

    if kind == "architect":
        return "\n".join([
            salutation,
            "",
            f"Bumping this to the top of your inbox — wanted to check in on the Plan Review "
            f"note I sent about {project or 'your DC project'}.",
            "",
            f"No pressure at all. If there isn't a near-term need for {company}, totally "
            f"understood. But if you have a submittal coming up where a pre-DOB peer review "
            f"would be useful, happy to turn one around fast.",
            "",
            "Worth a quick call?",
        ])

    if kind == "gc":
        return "\n".join([
            salutation,
            "",
            f"Quick bump on my note {proj_ref} — wanted to make sure it didn't get buried.",
            "",
            f"If {company} hasn't locked in a Third-Party Inspector yet, we can stand up on "
            f"this project with same- or next-business-day scheduling and straightforward "
            f"per-visit billing.",
            "",
            "Open to a 5-minute call?",
        ])

    # owner_pr / generic
    return "\n".join([
        salutation,
        "",
        f"Following up on my earlier note {proj_ref}. Wanted to make sure it reached you.",
        "",
        f"If {company} is still evaluating Plan Review or Third-Party Inspection resources "
        f"for this project, happy to walk through how BCC typically slots in.",
        "",
        "Open to a quick call?",
    ])


# ── Touch 2 (Day 12): value-add, different angle ─────────────────────────────
def _touch2_body(first: str, company: str, project: str, kind: str) -> str:
    salutation = f"Hi {first}," if first else "Hi,"

    if kind == "architect":
        return "\n".join([
            salutation,
            "",
            f"Following up once more on {project or 'your DC project'} — and sharing one "
            f"specific angle in case it's relevant.",
            "",
            "The architects we work with most often use BCC for two things:",
            "",
            "1. **Pre-submission peer review** — we flag the code issues DOB reviewers "
            "typically catch (egress, occupancy load, fire ratings, plumbing fixture counts, "
            "ventilation) before you submit, so you don't eat a revision cycle.",
            "",
            "2. **Gap-sealing on smaller projects** — when the project doesn't warrant a "
            "full fire protection or MEP engineer of record, BCC reviews and seals the "
            "code-compliance side.",
            "",
            "Either of those sound useful for a current or upcoming project?",
        ])

    if kind == "gc":
        return "\n".join([
            salutation,
            "",
            f"One more note on {project or 'DC inspection work'} in case it's helpful.",
            "",
            "Two things GCs tell us matter most when picking a Third-Party Inspector:",
            "",
            "1. **Scheduling responsiveness** — we run same-day or next-business-day "
            "availability, so a failed rough-in doesn't park your trades for a week.",
            "",
            "2. **Honest billing** — you pay for visits actually performed, not an upfront "
            "estimate. If the project wraps in fewer visits, you pay less. No surprises.",
            "",
            f"If {company} is still open to adding us to the vendor list, happy to send a "
            f"quick rate sheet. Otherwise no worries.",
        ])

    return "\n".join([
        salutation,
        "",
        f"Last substantive note on {project or 'this project'} — wanted to share one "
        f"concrete way BCC usually helps owners / developers at this stage:",
        "",
        "**Single point of accountability for code compliance.** Instead of juggling a plan "
        "reviewer, an inspector, and an engineer of record on code questions, BCC covers "
        "all three under one engagement — so when DOB pushes back, you have one firm "
        "resolving it end-to-end.",
        "",
        f"If that's useful for {company} on a current or upcoming project, happy to talk.",
    ])


# ── Touch 3 (Day 24): break-up ───────────────────────────────────────────────
def _touch3_body(first: str, company: str, project: str, kind: str) -> str:
    salutation = f"Hi {first}," if first else "Hi,"
    proj = project or "your DC project"

    if kind == "architect":
        return "\n".join([
            salutation,
            "",
            f"I've circled back a couple of times on {proj} without hearing back, so I'll "
            f"close the loop on my end.",
            "",
            f"If {company} picks up a project down the road where a pre-DOB plan review or "
            f"code-compliance seal would help, we'd be glad to hear from you. I'll stop "
            f"pinging until then.",
            "",
            "Thanks for the time either way.",
        ])

    # gc / owner / generic — same tone, minor wording
    return "\n".join([
        salutation,
        "",
        f"Circled back on {proj} a couple of times without a reply — fully understand "
        f"inboxes are full, so I'll stop here on my end.",
        "",
        f"If {company} has a future project where a responsive Third-Party Inspector or "
        f"Plan Reviewer would help, we'd welcome the chance to quote. Otherwise no action "
        f"needed from your side.",
        "",
        "Appreciate the consideration.",
    ])


# ── Touch dispatch ───────────────────────────────────────────────────────────
# Windows (days since initial send): touch 1 ≥ 4, touch 2 ≥ 12, touch 3 ≥ 24
TOUCH_WINDOWS = {1: 4, 2: 12, 3: 24}


def _build_touch(first: str, company: str, project: str, kind: str, touch: int) -> str:
    if touch == 1:
        return _touch1_body(first, company, project, kind)
    if touch == 2:
        return _touch2_body(first, company, project, kind)
    if touch == 3:
        return _touch3_body(first, company, project, kind)
    raise ValueError(f"Invalid touch number: {touch}")


# ── Back-compat: old code paths still import these names ──────────────────────
def _followup_body_inspection(first: str, company: str, project: str) -> str:
    return _touch1_body(first, company, project, "gc")


def _followup_body_plan_review(first: str, company: str, project: str) -> str:
    return _touch1_body(first, company, project, "owner_pr")


def _followup_subject(original_subject: str, has_plan_review: bool,
                      company: str = "", project: str = "", touch: int = 1) -> str:
    """Generate follow-up subject line — mirror the short new subject style."""
    m = re.search(r"(?:Services for|for)\s+(.+?)(?:\s*\||\s*—|$)", original_subject)
    project_short = m.group(1).strip() if m else ""
    if not project_short:
        project_short = project or (f"{company} DC Projects" if company else "Your DC Project")

    # Keep subject ≤ 55 chars so it survives mobile truncation
    prefix_by_touch = {1: "Re: ", 2: "Following up — ", 3: "Closing the loop — "}
    prefix = prefix_by_touch.get(touch, "Re: ")
    body = f"Plan Review for {project_short} — BCC" if has_plan_review else f"TPI Inspector for {project_short} — BCC"
    full = prefix + body
    if len(full) > 72:
        # Fall back to shorter form
        if has_plan_review:
            full = f"{prefix.strip()} Plan Review — BCC"
        else:
            full = f"{prefix.strip()} TPI Inspector — BCC"
    return full


# ── Load follow-up candidates ────────────────────────────────────────────────
def _parse_ts(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat((s or "").replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def load_followup_candidates(only_touch: int | None = None) -> list[dict]:
    """
    Read sent_log.csv and return contacts due for a specific touch (1/2/3).
    Uses DictReader so column pollution in ``replied`` is safe.

    Touch schedule (days since last send event):
      Touch 1: ≥ 4 days since sent_at, followup_count == 0
      Touch 2: ≥ 8 days since last_followup_at, followup_count == 1
      Touch 3: ≥ 12 days since last_followup_at, followup_count == 2
    """
    if not SENT_LOG.exists():
        return []

    now = datetime.now(timezone.utc)
    candidates = []
    seen_emails: set[str] = set()

    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = (row.get("contact_email") or "").strip()
            if not email:
                continue

            name      = (row.get("contact_name") or "").strip()
            company   = (row.get("company") or "").strip()
            project   = (row.get("project") or "").strip()
            subject   = (row.get("subject") or "").strip()
            sent_at   = _parse_ts(row.get("sent_at") or "")
            if not sent_at:
                continue

            replied_val = (row.get("replied") or "").strip()

            # followup_count column: preferred new field.
            # Fallback for legacy rows: 1 if followup_sent_at or last_followup_at has a timestamp, else 0.
            try:
                touch_done = int((row.get("followup_count") or "0").strip() or "0")
            except ValueError:
                touch_done = 0
            legacy_followup = (row.get("last_followup_at") or row.get("followup_sent_at") or "").strip()
            if touch_done == 0 and legacy_followup and "T" in legacy_followup:
                touch_done = 1

            last_event = _parse_ts(legacy_followup) or sent_at

            email_lower = email.lower()
            if _is_gov(email_lower, company):
                continue
            if _is_replied(replied_val):
                continue
            if touch_done >= 3:
                continue
            if email_lower in seen_emails:
                continue

            next_touch = touch_done + 1
            days_since_last = (now - last_event).days

            window = TOUCH_WINDOWS.get(next_touch, 999)
            if days_since_last < window:
                continue
            if only_touch is not None and next_touch != only_touch:
                continue

            seen_emails.add(email_lower)
            has_plan_review = "Plan Review" in subject
            kind = _infer_target_kind(subject, company)

            candidates.append({
                "email": email,
                "email_lower": email_lower,
                "name": name,
                "company": company,
                "project": project,
                "original_subject": subject,
                "sent_at": row.get("sent_at") or "",
                "days_since_last": days_since_last,
                "has_plan_review": has_plan_review,
                "kind": kind,
                "touch": next_touch,
            })

    return candidates


def _log_followup(email_addr: str, sent_from: str, touch: int) -> None:
    """Mark a follow-up as sent for ``email_addr`` — increments followup_count
    and updates last_followup_at. Uses DictReader/DictWriter so the read side
    is resilient to column pollution.

    If the CSV lacks followup_count / last_followup_at columns, they are
    added (migration-safe: all old rows get followup_count=1 if the legacy
    followup_sent_at was populated, else 0).
    """
    if not SENT_LOG.exists():
        return

    target = email_addr.strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Read all rows as dicts
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = list(reader.fieldnames or [])

    # Ensure new columns exist
    changed_header = False
    for col in ("followup_count", "last_followup_at"):
        if col not in header:
            header.append(col)
            changed_header = True

    # Locate and update the target row (first match only)
    updated = False
    for r in rows:
        # Backfill legacy counts
        if "followup_count" not in r or (r.get("followup_count") or "") == "":
            legacy = (r.get("followup_sent_at") or "").strip()
            r["followup_count"] = "1" if legacy and "T" in legacy else "0"
        if (r.get("last_followup_at") or "") == "":
            r["last_followup_at"] = (r.get("followup_sent_at") or "").strip()

        if not updated and (r.get("contact_email") or "").strip().lower() == target:
            try:
                prev = int((r.get("followup_count") or "0").strip() or "0")
            except ValueError:
                prev = 0
            r["followup_count"] = str(max(prev, touch))
            r["last_followup_at"] = now_iso
            updated = True

    # Rewrite
    with open(SENT_LOG, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Follow-up sender for CW cold outreach")
    ap.add_argument("--send", action="store_true", help="Actually send (default: preview)")
    ap.add_argument("--dry-run", action="store_true", help="Show full email bodies")
    ap.add_argument("--limit", type=int, default=40, help="Max follow-ups to send (default: 40)")
    ap.add_argument("--sender", choices=["both", "admin", "ycao"], default="both",
                    help="Which account(s) to send from")
    ap.add_argument("--touch", type=int, choices=[1, 2, 3], default=None,
                    help="Only send this touch (1=day4 bump, 2=day12 value-add, 3=day24 break-up)")
    ap.add_argument("--delay", type=int, default=5,
                    help="Seconds between emails (default: 5)")
    args = ap.parse_args()

    candidates = load_followup_candidates(only_touch=args.touch)

    if not candidates:
        print("No follow-up candidates found.")
        print("  (All contacts either too recent, already replied, DC gov, or already followed up)")
        return 0

    # Apply limit
    batch = candidates[:args.limit]

    # Determine sender split
    if args.sender == "admin":
        admin_batch = batch
        ycao_batch = []
    elif args.sender == "ycao":
        admin_batch = []
        ycao_batch = batch
    else:
        half = len(batch) // 2
        admin_batch = batch[:half]
        ycao_batch = batch[half:]

    print(f"\n{'='*65}")
    print(f"CW Cold Outreach Follow-Up Sender")
    print(f"{'='*65}")
    print(f"  Total candidates:    {len(candidates)}")
    print(f"  This batch:          {len(batch)}")
    if args.sender == "both":
        print(f"    admin@:            {len(admin_batch)}")
        print(f"    ycao@:             {len(ycao_batch)}")
    else:
        print(f"    {args.sender}@:            {len(batch)}")
    print()

    # Preview
    for i, c in enumerate(batch, 1):
        use_ycao = c in ycao_batch
        sender_tag = "ycao@" if use_ycao else "admin@"
        print(f"  {i:>3}. [{sender_tag}] T{c['touch']} {c['kind']:<10} "
              f"{c['name']:<26} {c['company']:<32} +{c['days_since_last']}d")

        if args.dry_run:
            first = _first_name(c["name"])
            body = _build_touch(first, c["company"], c["project"], c["kind"], c["touch"])
            subject = _followup_subject(c["original_subject"], c["has_plan_review"],
                                        c["company"], c["project"], touch=c["touch"])
            print(f"       Subject: {subject}")
            print(f"       Body:\n")
            for line in body.split("\n"):
                print(f"         {line}")
            print()

    if args.dry_run:
        print("[dry-run] No emails sent.")
        return 0

    if not args.send:
        print(f"\nRun with --send to send {len(batch)} follow-up email(s).")
        print(f"  python send_cw_followups.py --send")
        print(f"  python send_cw_followups.py --dry-run   # preview bodies first")
        return 0

    # Confirm
    confirm = input(
        f"\nSend {len(batch)} follow-up emails? (Y to confirm): "
    ).strip()
    if confirm.upper() != "Y":
        print("Aborted.")
        return 0

    # Send
    print(f"\nSending {len(batch)} follow-up email(s) ({args.delay}s delay)...\n")
    sent_count = 0

    for c in batch:
        first = _first_name(c["name"])
        body = _build_touch(first, c["company"], c["project"], c["kind"], c["touch"])
        subject = _followup_subject(c["original_subject"], c["has_plan_review"],
                                    c["company"], c["project"], touch=c["touch"])

        use_ycao = c in ycao_batch
        sender_label = "ycao@" if use_ycao else "admin@"
        sent_from = "ycao@buildingcodeconsulting.com" if use_ycao else "admin@buildingcodeconsulting.com"

        if use_ycao:
            ok, msg = send_from_ycao(c["email"], subject, body)
        else:
            ok, msg = send_from_admin(c["email"], subject, body)

        if ok:
            print(f"  OK  [{sender_label}] T{c['touch']} {c['name']} <{c['email']}> ({c['company']})")
            _log_followup(c["email_lower"], sent_from, c["touch"])
            sent_count += 1
        else:
            print(f"  FAIL[{sender_label}] {c['email']} — {msg}")

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\nDone. Sent {sent_count}/{len(batch)} follow-up emails.")
    return 0 if sent_count == len(batch) else 1


if __name__ == "__main__":
    # Cross-machine lock only on real sends; previews and dry-runs run unwrapped
    # so the other machine can preview/draft in parallel without blocking.
    if "--send" in sys.argv and "--dry-run" not in sys.argv:
        from core_tools.active_operator import operator_lock
        with operator_lock("send_cw_followups.py"):
            sys.exit(main())
    else:
        sys.exit(main())
