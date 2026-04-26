"""
migrate_sent_log.py — One-shot migration for sent_log.csv column pollution.

Problem (documented 2026-04-24):
An earlier version of send_cw_followups.py / daily_sender.py wrote the
sender address (admin@... / ycao@...) into the `replied` column by mistake.
Of 113 rows, 87 are polluted this way. Only value "1" means an actual reply.

This migration:
  1. Backs up sent_log.csv to sent_log.csv.bak.<timestamp>
  2. Adds two columns if missing: `followup_count` (int) + `last_followup_at`
  3. For every row:
     - If `replied` is an email address (contains '@'), clear it (bogus value)
     - If legacy `followup_sent_at` has a timestamp and `followup_count` is
       empty/0, set followup_count=1 and copy the timestamp to last_followup_at
  4. Writes the cleaned CSV back in place.

Run once:
    python migrate_sent_log.py           # dry-run: show what would change
    python migrate_sent_log.py --apply   # actually rewrite the file
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SENT_LOG = BASE_DIR / "sent_log.csv"


def _is_bogus_replied(val: str) -> bool:
    """Return True if the ``replied`` value is a stray email address, not a real flag."""
    v = (val or "").strip().lower()
    if not v:
        return False
    if v in ("1", "true", "yes"):
        return False
    return "@" in v  # treat any address-like string as pollution


def migrate(apply: bool) -> int:
    if not SENT_LOG.exists():
        print(f"sent_log.csv not found at {SENT_LOG}")
        return 1

    # Read everything
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = list(reader.fieldnames or [])

    print(f"Loaded {len(rows)} rows. Header: {header}")

    # Add new columns if missing
    new_cols: list[str] = []
    for col in ("followup_count", "last_followup_at"):
        if col not in header:
            header.append(col)
            new_cols.append(col)
    if new_cols:
        print(f"  Adding columns: {new_cols}")

    # Count what we'll change
    pollution_cleared = 0
    counts_set = 0
    timestamps_copied = 0

    for r in rows:
        # Clear polluted `replied` values
        if _is_bogus_replied(r.get("replied", "")):
            r["replied"] = ""
            pollution_cleared += 1

        # Backfill followup_count
        legacy_ts = (r.get("followup_sent_at") or "").strip()
        has_ts = bool(legacy_ts) and "T" in legacy_ts
        current_count = (r.get("followup_count") or "").strip()
        if not current_count:
            r["followup_count"] = "1" if has_ts else "0"
            if has_ts:
                counts_set += 1

        # Backfill last_followup_at
        if not (r.get("last_followup_at") or "").strip():
            if has_ts:
                r["last_followup_at"] = legacy_ts
                timestamps_copied += 1
            else:
                r["last_followup_at"] = ""

    print(f"  Polluted `replied` values cleared:   {pollution_cleared}")
    print(f"  Followup_count set to 1 from legacy: {counts_set}")
    print(f"  Last_followup_at backfilled:         {timestamps_copied}")

    if not apply:
        print("\n[dry-run] No changes written. Run with --apply to commit.")
        return 0

    # Back up
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = SENT_LOG.with_suffix(f".csv.bak.{stamp}")
    shutil.copy2(SENT_LOG, backup)
    print(f"\nBackup written: {backup.name}")

    # Rewrite
    with open(SENT_LOG, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Rewrote {SENT_LOG.name} with {len(header)} columns.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Clean sent_log.csv column pollution")
    ap.add_argument("--apply", action="store_true", help="Rewrite the file (otherwise dry-run)")
    args = ap.parse_args()
    return migrate(apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
