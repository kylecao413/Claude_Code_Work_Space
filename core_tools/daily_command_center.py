"""
Generate a zero-AI daily command center brief for BCC/KCY.

This script intentionally does not call any LLM, browser, email sender, or API.
It reads local operational files and writes a reviewable Markdown brief.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Command_Center"


def _read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit is not None and len(text) > limit:
        return text[:limit] + "\n\n[truncated]\n"
    return text


def load_work_log() -> dict:
    path = ROOT / "work_log.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"__error__": f"Could not parse {path.name}"}


def list_markdown_files(folder: Path, limit: int = 20) -> list[Path]:
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def summarize_work_log(work_log: dict) -> tuple[Counter, list[tuple[str, dict]]]:
    counts: Counter = Counter()
    drafted: list[tuple[str, dict]] = []
    for key, item in work_log.items():
        if key.startswith("__"):
            continue
        if not isinstance(item, dict):
            continue
        status = item.get("status") or "unknown"
        counts[status] += 1
        if status == "email_drafted":
            drafted.append((key, item))
    drafted.sort(key=lambda kv: kv[1].get("email_drafted", ""), reverse=True)
    return counts, drafted


def load_sent_stats() -> tuple[int, list[dict]]:
    path = ROOT / "sent_log.csv"
    if not path.exists():
        return 0, []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return len(rows), rows[-10:]


def extract_review_summary() -> str:
    review_path = ROOT / "Pending_Approval" / "To_Review" / "00_REVIEW_THESE.md"
    text = _read_text(review_path, limit=4000)
    if not text:
        return "- No `00_REVIEW_THESE.md` file found."
    lines = []
    for line in text.splitlines():
        if line.startswith("**") or line.startswith("- ") or line.startswith("## ") or line.startswith("### "):
            lines.append(line)
        if len(lines) >= 40:
            break
    return "\n".join(lines) if lines else text[:1200]


def build_brief(today: str) -> str:
    work_log = load_work_log()
    status_counts, drafted = summarize_work_log(work_log)
    sent_total, sent_recent = load_sent_stats()

    outbound = list_markdown_files(ROOT / "Pending_Approval" / "Outbound", limit=20)
    to_review = list_markdown_files(ROOT / "Pending_Approval" / "To_Review", limit=20)

    bc_new = _read_text(ROOT / "bc_bidboard_new_projects.md", limit=3500)
    pe_readme = _read_text(ROOT / "PE_State_Applications" / "README.md", limit=2500)
    fairfax_script = ROOT / "fairfax_3pi_submit.py"
    fairfax_exists = fairfax_script.exists()

    lines: list[str] = []
    lines.append(f"# BCC/KCY Daily Command Center - {today}")
    lines.append("")
    lines.append("Generated locally with no AI/API calls.")
    lines.append("")

    lines.append("## 1. Executive Snapshot")
    if status_counts:
        for status, count in status_counts.most_common():
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- No work log status data found.")
    lines.append(f"- Sent log rows: {sent_total}")
    lines.append(f"- Pending outbound draft files scanned: {len(outbound)}")
    lines.append(f"- Pending review draft files scanned: {len(to_review)}")
    lines.append(f"- Fairfax 3PI submit helper present: {'yes' if fairfax_exists else 'no'}")
    lines.append("")

    lines.append("## 2. Today's Human Decisions")
    lines.append("- Decide which `email_drafted` projects should be sent, deleted, or revised.")
    lines.append("- Do not run any send script without explicit Kyle approval.")
    lines.append("- For any Fairfax request/report/completion, run `fairfax_3pi_submit.py --dry-run` first.")
    lines.append("- For any scraper breakage, investigate before patching; update `BCC_PROPOSAL_RULES.md` when a selector is confirmed.")
    lines.append("")

    lines.append("## 3. Work Log - Recent Drafted Items")
    if drafted:
        for key, item in drafted[:20]:
            draft = item.get("draft_path", "")
            when = item.get("email_drafted", "")
            lines.append(f"- {when} | {key}")
            if draft:
                lines.append(f"  Draft: `{draft}`")
    else:
        lines.append("- No `email_drafted` items found.")
    lines.append("")

    lines.append("## 4. Pending Approval - Outbound")
    if outbound:
        for path in outbound:
            rel = path.relative_to(ROOT)
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            lines.append(f"- {mtime} | `{rel}`")
    else:
        lines.append("- No outbound drafts found.")
    lines.append("")

    lines.append("## 5. Pending Approval - To Review")
    lines.append(extract_review_summary())
    lines.append("")

    lines.append("## 6. New BuildingConnected Bid Board Items")
    lines.append(bc_new.strip() if bc_new else "- No `bc_bidboard_new_projects.md` found.")
    lines.append("")

    lines.append("## 7. PE / KCY License Expansion")
    lines.append(pe_readme.strip() if pe_readme else "- No PE State Applications README found.")
    lines.append("")

    lines.append("## 8. Recent Sent Log Rows")
    if sent_recent:
        for row in sent_recent:
            sent_at = row.get("sent_at", "")
            company = row.get("company", "")
            project = row.get("project", "")
            subject = row.get("subject", "")
            lines.append(f"- {sent_at} | {company} | {project} | {subject}")
    else:
        lines.append("- No sent log rows found.")
    lines.append("")

    lines.append("## 9. Recommended AI Routing")
    lines.append("- Codex: daily management, final review, risk triage, browser/screenshot-heavy tasks.")
    lines.append("- Claude Code: bounded implementation, local refactors, batch file generation, tests.")
    lines.append("- Gemini Pro web: deep research, large-document synthesis, web page reading, second-opinion review.")
    lines.append("- Gemini API: only when web UI is not enough or automation needs a structured programmatic answer.")
    lines.append("")

    lines.append("## 10. Safety Rules")
    lines.append("- Never store ChatGPT/Google/Claude account passwords in `.env`.")
    lines.append("- Prefer browser profiles or OAuth/API tokens with narrow scope.")
    lines.append("- Never send email, submit county forms, or change official filings without explicit approval.")
    lines.append("- Do not publish or paste secrets from `.env`, cookies, browser profiles, or credential files.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate BCC/KCY daily command center brief.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--print", action="store_true", help="Print the output path only.")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    brief = build_brief(args.date)
    out_path = OUT_DIR / f"Daily_Command_Center_{args.date}.md"
    out_path.write_text(brief, encoding="utf-8")

    if args.print:
        print(out_path)
    else:
        print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
