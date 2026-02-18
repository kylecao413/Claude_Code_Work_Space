# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Your Role: Executor + Self-Reviewer

You write code, run tools, manipulate files, and review your own work before deploying. You do NOT need to call ask_senior for routine code work — use your own judgment.

### Self-Review Checklist (apply before running new scripts)

Before executing any new or significantly changed script, mentally verify:

1. **Business rule compliance** — Email bodies follow BCC_PROPOSAL_RULES.md (no signature, billing disclaimer present, no plan review for GC targets, no "Proposal" language in cold outreach subjects)
2. **Security** — No hardcoded credentials, no command injection, no secrets in outputs
3. **Logic correctness** — Loops terminate, edge cases handled (empty lists, missing fields, expired cookies)
4. **Email safety** — Human approval required before any send; no accidental batch-send without Y confirmation
5. **File safety** — No accidental deletion of non-temp files; old draft cleanup only targets known prefixes (CW_*, Email_*)

### When to Act Immediately (no extra review needed)

- Bug fixes, typos, single-line changes
- Running existing tested scripts
- File reads, git status, work_log checks
- Following an already-approved plan

### When to Pause and Think Before Coding

- New scripts touching email sending or external APIs
- Changes to fee calculations or proposal content
- Refactors across 3+ files
- Anything that could send real emails or modify shared data

### ask_senior.py — Use Only When User Explicitly Requests

`core_tools/ask_senior.py` is available but no longer mandatory. Only call it when:
- User explicitly says "ask senior", "get Gemini review", or "review with AI"
- Complex multimodal analysis (screenshots, PDF review)

## Workflow: Draft → Self-Review → Test → Run

1. **Draft** — Write the code
2. **Self-Review** — Apply the checklist above; fix any issues found
3. **Test** — Run `python -m pytest` for logic-heavy scripts
4. **Run** — Execute and verify output

## Commands

```bash
# Run tests
python -m pytest

# Consult Senior Architect (default: gemini-2.5-pro)
python core_tools/ask_senior.py <file> "<question>"
python core_tools/ask_senior.py <file> "<question>" --model gemini-2.5-flash  # cheaper, for batch/routine
# Examples:
python core_tools/ask_senior.py proposal_generator.py "Is the fee calculation logic correct for multi-discipline projects?"
python core_tools/ask_senior.py screenshot.png "Does this UI layout match our proposal template spec?"

# Telegram handoff (zero AI cost)
python core_tools/handoff_to_telegram.py

# Lead scraping
python constructionwire_dc_leads.py
python buildingconnected_bid_scraper.py

# Proposal pipeline (3 phases: BC extract → generate+audit → hand-off)
python run_master_proposal_pipeline.py

# Approval monitor daemon
python approval_monitor.py
```

## Architecture: Hybrid Intelligence QA

This system follows a **dual-brain architecture** as described in the 2026 QA blueprint:

| Layer | Component | Role |
|-------|-----------|------|
| **Brain** (Senior Architect) | Gemini 2.5 Pro via `ask_senior.py` | Logic review, architecture decisions, security audit, multimodal analysis |
| **Hands** (Executor) | Claude Code (you) | Code writing, file manipulation, test execution, git operations |
| **Eye** (Perception) | `deep_search_contacts.py` (DuckDuckGo + Gemini API) | Deep research, contact discovery |
| **Tools** | Playwright, pytest, email_sender | Browser automation, testing, email delivery |
| **Memory** | `.cursorrules`, `BCC_PROPOSAL_RULES.md`, `CLAUDE.md` | Persistent project knowledge and rules |

### Data Flow

1. **Leads** — `constructionwire_dc_leads.py` / `buildingconnected_bid_scraper.py` scrape projects via Playwright. Cookies in `.constructionwire_cookies.json` / `.buildingconnected_cookies.json`.
2. **Research** — `deep_search_contacts.py` (DuckDuckGo + Gemini API). Output: `Research_[Company].md`.
3. **Proposals** — `proposal_generator.py` fills Word templates from `BuildingConnected/templates/`. Output: `../Projects/[Client]/[Project]/`. Master pipeline: `run_master_proposal_pipeline.py`.
4. **Email** — `email_sender.py` sends via `admin@buildingcodeconsulting.com`, CC `ycao@`. Drafts in `Pending_Approval/Outbound/`. `approval_monitor.py` watches for `-OK` renames.
5. **Mobile** — `telegram_bot.py` for approvals, briefings, `/save` writes tasks to `Inbox/ACTIVE_TASK.md`.

## Critical Business Rules

### Email: Human Approval Required (No Exceptions)
All email sends require explicit user confirmation ("Y" or "Proceed with sending"). Display: `Email content ready for [Contact]. Please review '[path]' and type 'Y' to send.` Send from `admin@buildingcodeconsulting.com`, CC `ycao@`. Do NOT append signatures (auto-signatures enabled on both accounts).

### Proposals: Obey BCC_PROPOSAL_RULES.md
Before generating any proposal, read `BCC_PROPOSAL_RULES.md`. Client name, contact, address, description, and fees must come from real BuildingConnected data — never placeholders. All text must be black. Fee tiers: $295 (large volume) → $375–400 (one-time/complex).

### Scraping Rule Fixation
When a correct scraping method is found, immediately record it in `BCC_PROPOSAL_RULES.md` § 0. Do not just fix the code — update the rules file so the knowledge persists.

### Anti-Spam Email Subjects
For each lead, generate 3 subject lines (Plan Review angle, Inspection angle, project-specific angle), randomly pick one. Never reuse the same template across leads.

### Check Inbox: Consult Work Log First (No Exceptions)
Before generating any proposal or drafting any email, run:
```
python core_tools/work_log.py --status
```
Skip any project where proposal is already done (no regeneration).
Skip any project where email was sent and follow-up is not yet due.
Only act on: new projects, projects needing email draft, or follow-ups due.
Default follow-up interval: 4 days.

### Service Territory
- **Inspection**: DC, Northern VA, PG County, Montgomery County only
- **Plan Review**: nationwide/global
- **Code Consulting**: up to Baltimore (north), Norfolk (south), ~2.5 hr from Northern VA

## Structured Output & Quality Gates

Per the QA architecture, avoid relying on vague natural-language judgments. When reporting review results or test outcomes:
- Use structured format (JSON or markdown tables) with: error type, file location, severity
- AI-suggested fixes must be verified by running `python -m pytest` — passing tests are the gate, not AI's opinion
- For proposal verification, the master pipeline internal audit (Phase 2) is the QA gate — passing audit is the acceptance criterion

## Cost Control Rules

API costs must be minimized. Follow these rules strictly:

- **ask_senior**: Only when user explicitly requests it. Default model: gemini-2.5-flash (cheaper); use gemini-2.5-pro only when user asks for deeper review.
- **Email sending**: Zero AI cost. `email_sender.py` uses SMTP directly. Do NOT use AI to send emails.
- **Proposal generation**: `proposal_generator.py` fills Word templates locally (zero AI cost). Gemini review in Phase 3 is optional.
- **Research**: Use `deep_search_contacts.py`; use `--model gemini-2.5-flash` flag if it supports it to minimize cost
- **inbox_watcher**: SHELVED. Do not run `core_tools/inbox_watcher.py` — it triggers `claude -p` which costs API tokens per invocation. Instead, user manually says "Check Inbox" when back at desk.
- **Telegram handoff**: `core_tools/handoff_to_telegram.py` uses `requests` only (zero AI cost), safe to run anytime.

## Environment

- Python with `python-dotenv`; credentials in `.env` (never committed)
- Browser automation: Playwright (not Selenium)
- Working language: Chinese + English mix; user communicates in both
