"""
drip_sender.py — Multi-account, time-sliced email drip sender.

Unlike daily_sender.py / send_cw_followups.py (which burst with 5s delays),
this script:
  1. Distributes each account's daily cap across N time slots (e.g. 9am / 12pm / 3pm)
  2. Randomizes each send with 60-120s jitter to mimic human cadence
  3. Runs accounts in parallel threads (one account doesn't block the others)
  4. Waits until slot start time before sending (session must stay open)
  5. Supports resume: re-running skips emails already in sent_log

Supported accounts:
  - admin  → admin@buildingcodeconsulting.com  (PRIV_MAIL1)
  - ycao   → ycao@buildingcodeconsulting.com   (PRIV_MAIL2)
  - kcy    → ycao@kcyengineer.com              (PRIV_MAIL3, KCY brand)

Modes:
  - followup  → Load uncontacted candidates from sent_log.csv (BCC accounts only)
  - new       → Load CW_*.md drafts from Pending_Approval/Outbound (BCC accounts only)

Examples:
  # Today's BCC drip: 30 admin + 30 ycao, 3 slots, follow-ups only
  python drip_sender.py --mode followup --accounts admin=30,ycao=30 --slots 9,12,15 --send

  # Compress into one window starting now (all past slots)
  python drip_sender.py --mode followup --accounts admin=20,ycao=20 --slots now --send

  # Dry-run preview
  python drip_sender.py --mode followup --accounts admin=30,ycao=30 --slots 9,12,15 --dry-run

  # KCY warm-up once DNS is live
  python drip_sender.py --mode new --accounts kcy=5 --slots 10,14 --send
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from email_sender import (
    send_from_admin, send_from_ycao, send_from_kcy,
)

# Reuse follow-up candidate loader + body generators from existing script
from send_cw_followups import (
    load_followup_candidates,
    _followup_body_inspection,
    _followup_body_plan_review,
    _followup_subject,
    _first_name,
    _log_followup,
)

BASE_DIR = Path(__file__).resolve().parent
SENT_LOG = BASE_DIR / "sent_log.csv"
ET       = ZoneInfo("America/New_York")

# ── Per-account sender map ───────────────────────────────────────────────────
ACCOUNT_SENDERS: dict[str, Callable] = {
    "admin": send_from_admin,
    "ycao":  send_from_ycao,
    "kcy":   send_from_kcy,
}

ACCOUNT_LABELS = {
    "admin": "admin@bcc",
    "ycao":  "ycao@bcc",
    "kcy":   "ycao@kcy",
}

# Flag set by SIGINT handler so in-flight slots finish gracefully
_abort = threading.Event()


def _install_sigint() -> None:
    def _handler(signum, frame):
        if _abort.is_set():
            print("\n[drip] Second Ctrl-C — hard exit.")
            sys.exit(130)
        print("\n[drip] Ctrl-C received — finishing current email, then stopping.")
        _abort.set()
    signal.signal(signal.SIGINT, _handler)


# ── Schedule construction ────────────────────────────────────────────────────
@dataclass
class SendItem:
    scheduled_at: datetime   # UTC
    account:      str
    candidate:    dict       # follow-up candidate dict


def _parse_accounts(spec: str) -> dict[str, int]:
    """Parse 'admin=30,ycao=30,kcy=0' into {'admin': 30, 'ycao': 30, 'kcy': 0}."""
    out: dict[str, int] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Bad --accounts entry: {part!r} (expected NAME=N)")
        name, n = part.split("=", 1)
        name = name.strip().lower()
        if name not in ACCOUNT_SENDERS:
            raise ValueError(f"Unknown account: {name!r} (valid: admin/ycao/kcy)")
        out[name] = int(n.strip())
    return out


def _parse_slots(spec: str, now_et: datetime) -> list[datetime]:
    """Parse '9,12,15' into a list of ET datetimes for today.

    Special value 'now' → single slot starting immediately.
    Past slots (before current time) are dropped; if all are past, compress
    the remaining batch into a single slot starting now.
    """
    if spec.strip().lower() == "now":
        return [now_et]

    hours: list[int] = []
    for h in spec.split(","):
        h = h.strip()
        if not h:
            continue
        hours.append(int(h))

    today = now_et.date()
    all_slots = [
        datetime.combine(today, dtime(h, 0), tzinfo=ET) for h in sorted(hours)
    ]
    future_slots = [s for s in all_slots if s > now_et]

    if not future_slots:
        # All slots past — compress into a single immediate window
        print(f"[drip] All configured slots are past {now_et.strftime('%H:%M')} ET — "
              f"compressing into a single window starting now.")
        return [now_et]
    return future_slots


def _parse_jitter(spec: str) -> tuple[int, int]:
    """Parse '60-120' into (60, 120)."""
    if "-" not in spec:
        n = int(spec)
        return (n, n)
    lo, hi = spec.split("-", 1)
    return (int(lo), int(hi))


def build_schedule(
    candidates_by_account: dict[str, list[dict]],
    per_account_cap:       dict[str, int],
    slots:                 list[datetime],
    jitter:                tuple[int, int],
) -> list[SendItem]:
    """Construct timestamped send schedule.

    For each account:
      - Slice candidates to the daily cap
      - Distribute roughly evenly across slots (first slots get the extras)
      - Within a slot, each send is spaced by random jitter[lo..hi] seconds

    Result is sorted by scheduled_at.
    """
    schedule: list[SendItem] = []

    for account, cap in per_account_cap.items():
        if cap <= 0:
            continue
        cands = candidates_by_account.get(account, [])[:cap]
        if not cands:
            continue

        n_slots = len(slots)
        base = len(cands) // n_slots
        extras = len(cands) - base * n_slots

        idx = 0
        for slot_i, slot_start in enumerate(slots):
            slot_count = base + (1 if slot_i < extras else 0)
            slot_offset_sec = 0.0
            for _ in range(slot_count):
                if idx >= len(cands):
                    break
                # First email in slot starts at slot_start + small delay (5-15s)
                # to avoid all accounts firing at exactly the same second.
                if slot_offset_sec == 0.0:
                    slot_offset_sec = random.uniform(5, 15)
                else:
                    slot_offset_sec += random.uniform(jitter[0], jitter[1])
                ts = slot_start + timedelta(seconds=slot_offset_sec)
                schedule.append(SendItem(
                    scheduled_at=ts.astimezone(timezone.utc),
                    account=account,
                    candidate=cands[idx],
                ))
                idx += 1

    schedule.sort(key=lambda it: it.scheduled_at)
    return schedule


# ── Candidate loading (follow-up mode) ───────────────────────────────────────
def load_and_split_followup_candidates(
    accounts: list[str],
    min_days: int = 4,
) -> dict[str, list[dict]]:
    """Load follow-up candidates and split round-robin across accounts.

    Returns {account_name: [candidate_dicts]}. Only BCC accounts (admin/ycao)
    pull from sent_log — kcy has no history there yet.
    """
    bcc_accounts = [a for a in accounts if a in ("admin", "ycao")]
    out: dict[str, list[dict]] = {a: [] for a in accounts}

    if not bcc_accounts:
        return out

    all_cands = load_followup_candidates(min_days=min_days)
    # Round-robin across BCC accounts: index i → bcc_accounts[i % len]
    for i, cand in enumerate(all_cands):
        acct = bcc_accounts[i % len(bcc_accounts)]
        out[acct].append(cand)

    return out


# ── Execution ────────────────────────────────────────────────────────────────
def _send_one(item: SendItem) -> tuple[bool, str]:
    """Build subject + body for the candidate's mode and dispatch via the
    correct account sender. Currently supports only follow-up mode; extending
    to 'new' mode would plumb in the CW_*.md draft body instead."""
    c = item.candidate
    first = _first_name(c["name"])

    if c["has_plan_review"]:
        body = _followup_body_plan_review(first, c["company"], c["project"])
    else:
        body = _followup_body_inspection(first, c["company"], c["project"])

    subject = _followup_subject(
        c["original_subject"], c["has_plan_review"], c["company"], c["project"]
    )

    send_fn = ACCOUNT_SENDERS[item.account]
    return send_fn(c["email"], subject, body)


def _account_from_label(account: str) -> str:
    """Map account key to the sent_from email logged into sent_log.csv."""
    return {
        "admin": "admin@buildingcodeconsulting.com",
        "ycao":  "ycao@buildingcodeconsulting.com",
        "kcy":   "ycao@kcyengineer.com",
    }[account]


def run_schedule(schedule: list[SendItem], dry_run: bool) -> int:
    """Walk the schedule sequentially. Wait until each send's scheduled_at,
    then dispatch. Abort gracefully on SIGINT."""
    sent_count = 0
    total = len(schedule)

    for i, item in enumerate(schedule, 1):
        if _abort.is_set():
            print(f"[drip] Aborted after {sent_count}/{total}.")
            break

        now = datetime.now(timezone.utc)
        wait_s = (item.scheduled_at - now).total_seconds()
        local = item.scheduled_at.astimezone(ET).strftime("%H:%M:%S")
        tag = f"[{i:>3}/{total}] {local} ET  {ACCOUNT_LABELS[item.account]:<10}"

        if wait_s > 0:
            # Print countdown summary for long waits
            if wait_s > 120:
                print(f"{tag}  waiting {int(wait_s//60)}m{int(wait_s%60):02d}s → "
                      f"{item.candidate['name']} ({item.candidate['company']})")
            # Sleep in 5s chunks so Ctrl-C is responsive
            end_at = time.monotonic() + wait_s
            while time.monotonic() < end_at:
                if _abort.is_set():
                    return sent_count
                time.sleep(min(5.0, end_at - time.monotonic()))

        c = item.candidate
        if dry_run:
            print(f"{tag}  [DRY] {c['name']:<28} <{c['email']:<38}> ({c['company']})")
            sent_count += 1
            continue

        ok, msg = _send_one(item)
        if ok:
            print(f"{tag}  OK   {c['name']:<28} <{c['email']:<38}> ({c['company']})")
            _log_followup(c["email_lower"], _account_from_label(item.account))
            sent_count += 1
        else:
            print(f"{tag}  FAIL {c['email']} — {msg}")

    return sent_count


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Time-sliced drip email sender across multiple accounts."
    )
    ap.add_argument("--mode", choices=["followup", "new"], default="followup",
                    help="followup = re-contact from sent_log; new = CW_*.md drafts (not yet wired)")
    ap.add_argument("--accounts", required=True,
                    help="Comma list of account=cap, e.g. 'admin=30,ycao=30,kcy=0'")
    ap.add_argument("--slots", default="9,12,15",
                    help="Comma list of slot hours in ET, or 'now'. Past slots auto-drop.")
    ap.add_argument("--jitter", default="60-120",
                    help="Per-email delay range in seconds, e.g. '60-120' or '90'")
    ap.add_argument("--min-days", type=int, default=4,
                    help="Followup: min days since original send (default: 4)")
    ap.add_argument("--send", action="store_true", help="Actually send (default: preview schedule)")
    ap.add_argument("--dry-run", action="store_true", help="Walk schedule but log instead of send")
    ap.add_argument("--yes", action="store_true",
                    help="Skip interactive Y/N confirm (for piped/background launches where stdin is unreliable)")
    args = ap.parse_args()

    if args.mode == "new":
        print("[drip] --mode new not yet implemented (use daily_sender.py for new drafts).")
        return 2

    try:
        per_account_cap = _parse_accounts(args.accounts)
    except ValueError as e:
        print(f"[drip] {e}")
        return 1

    if sum(per_account_cap.values()) == 0:
        print("[drip] All account caps are 0 — nothing to do.")
        return 0

    now_et = datetime.now(ET)
    slots = _parse_slots(args.slots, now_et)
    jitter = _parse_jitter(args.jitter)

    # Load + split candidates
    cands_by_account = load_and_split_followup_candidates(
        accounts=list(per_account_cap.keys()),
        min_days=args.min_days,
    )

    total_available = sum(len(v) for v in cands_by_account.values())
    print(f"\n{'='*72}")
    print("Drip Sender — Schedule Preview")
    print(f"{'='*72}")
    print(f"  Mode:               {args.mode}")
    print(f"  Accounts & caps:    {per_account_cap}")
    print(f"  Candidates loaded:  {total_available} across {len([v for v in cands_by_account.values() if v])} account(s)")
    print(f"  Slots (ET):         {[s.strftime('%H:%M') for s in slots]}")
    print(f"  Per-email jitter:   {jitter[0]}-{jitter[1]}s random")
    print(f"  Current ET:         {now_et.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Build schedule
    schedule = build_schedule(cands_by_account, per_account_cap, slots, jitter)
    if not schedule:
        print("[drip] Schedule is empty — no matching candidates for the specified caps.")
        return 0

    # Preview
    print(f"Schedule ({len(schedule)} send(s)):")
    print(f"  {'#':>3}  {'Time (ET)':<10}  {'Account':<10}  {'Contact':<28}  Company")
    for i, item in enumerate(schedule, 1):
        local = item.scheduled_at.astimezone(ET).strftime("%H:%M:%S")
        c = item.candidate
        print(f"  {i:>3}  {local:<10}  {ACCOUNT_LABELS[item.account]:<10}  "
              f"{c['name']:<28}  {c['company']}")

    last_ts = schedule[-1].scheduled_at.astimezone(ET)
    total_span = (schedule[-1].scheduled_at - schedule[0].scheduled_at).total_seconds() / 60
    print(f"\n  First send:  {schedule[0].scheduled_at.astimezone(ET).strftime('%H:%M:%S')} ET")
    print(f"  Last send:   {last_ts.strftime('%H:%M:%S')} ET")
    print(f"  Total span:  {total_span:.0f} minutes")

    if not args.send and not args.dry_run:
        print(f"\n[drip] Preview only. Add --send to execute (or --dry-run to walk schedule without sending).")
        return 0

    if not args.dry_run and not args.yes:
        confirm = input(
            f"\nExecute this drip schedule of {len(schedule)} email(s)? "
            f"Session must stay open until {last_ts.strftime('%H:%M')} ET. (Y to confirm): "
        ).strip()
        if confirm.upper() != "Y":
            print("Aborted.")
            return 0
    elif args.yes:
        print(f"\n[drip] --yes passed — skipping interactive confirm. "
              f"Session must stay open until {last_ts.strftime('%H:%M')} ET.")

    _install_sigint()
    print(f"\n[drip] Starting. Ctrl-C once = graceful stop (finish current, abort rest).\n")
    sent = run_schedule(schedule, dry_run=args.dry_run)
    print(f"\n[drip] Done. {'Would-send' if args.dry_run else 'Sent'}: {sent}/{len(schedule)}")
    return 0 if sent == len(schedule) else 1


if __name__ == "__main__":
    # Cross-machine lock only on real sends; previews and dry-runs run unwrapped.
    if "--send" in sys.argv and "--dry-run" not in sys.argv:
        from core_tools.active_operator import operator_lock
        with operator_lock("drip_sender.py"):
            sys.exit(main())
    else:
        sys.exit(main())
