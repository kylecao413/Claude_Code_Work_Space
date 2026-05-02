# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Skills (BCC-specific, adapted from gstack)

Three local skills live under `.claude/skills/`. Invoke via slash command or natural-language trigger.

| Skill | Trigger | Use for |
|-------|---------|---------|
| `/bcc-strategy` | "brainstorm", "should we", "is this worth it" | Pressure-test a new initiative (state expansion, new service line, new tool) with six forcing questions. Output: one-page decision doc in `Strategy/`. Do NOT write code inside this skill. |
| `/bcc-investigate` | "debug", "why is this broken", "it was working yesterday" | Root-cause investigation for scraper / email / proposal-generator failures. Iron Law: no fixes without a verified hypothesis. Known-pattern table covers CW/BC/SMTP/Telegram failure modes. |
| `/bcc-review` | "review this draft", "review before send", "check my diff" | Two modes: (1) outbound-draft review against BCC_PROPOSAL_RULES.md + MEMORY.md rules before Kyle approves; (2) code-diff review before running a changed script against real leads. |

Proactively invoke these skills instead of answering directly when the user's request matches a trigger. Each skill's `SKILL.md` has the full workflow.

## Repo Layout (orient here first)

| Path | Contents |
|------|----------|
| `core_tools/` | Operational backbone — locks, dispatch wrapper, work_log, IMAP audit, Telegram, ask_senior. See index below. |
| `BuildingConnected/templates/` | Word proposal templates filled by `proposal_generator.py`. |
| `Pending_Approval/Outbound/` | Email + proposal drafts staged for Kyle to approve via `-OK` rename. `*-SENT.md` after delivery. |
| `Inbox/` | `ACTIVE_TASK.md` is the Telegram→repo bridge (see watch pattern below); `TASK_STATUS.md` is reply channel. |
| `Wrap up/` | Plan Review wrap-up package workflow (5 docs, 17 steps); has its own `CLAUDE.md`. |
| `PE_State_Applications/` | FL/TX/NC/SC/MD/DC PE application packets, prefilled PDFs, AHJ trackers. |
| `Legal/` | KCY PLLC restatement filings, conversion docs (`generate_*.py`). |
| `Strategy/` | One-page decision docs output by `/bcc-strategy`. |
| `_drive_cache/` | JSON dumps from Drive MCP (input to `wrapup_from_sheets.py` step 2). |
| `../Projects/` | Sibling dir — actual client folders where proposals + wrap-up packages land. |

## core_tools/ index

| Tool | Purpose |
|------|---------|
| `work_log.py` | Pipeline status. NOT authoritative for formal-proposal sends — reconcile via inbox audit. |
| `bcc_inbox_audit.py` | IMAP 5-bucket reconciliation (admin@/ycao@). Run when work_log disagrees with reality. |
| `active_operator.py` | Phase 1 cross-machine cooperative lock at `<bridge>/ACTIVE_OPERATOR.txt`. Bridge auto-probes Google Drive (`G:/My Drive/claude-bridge` on Windows, `~/Library/CloudStorage/GoogleDrive-*/My Drive/claude-bridge` on Mac); override with `CLAUDE_BRIDGE_PATH`. |
| `bcc-remote.sh` | Phase 2 Mac→Windows dispatch wrapper (Tailscale + OpenSSH). |
| `handoff_to_telegram.py` | Mobile push (zero AI cost, `requests` only). |
| `telegram_approval.py` | Sync blocking approval loop. **Do not run alongside `telegram_bot.py`** — they share `getUpdates`. |
| `ask_senior.py` | Gemini review. Only when user explicitly requests. Default `--model gemini-2.5-flash`. |
| `inbox_watcher.py` | **SHELVED** — costs API tokens per `claude -p` invocation. Do not run. |

## Your Role: Executor + Self-Reviewer

You write code, run tools, manipulate files, and review your own work before deploying. You do NOT need to call ask_senior for routine code work — use your own judgment.

### Self-Review Checklist (apply before running new scripts)

Before executing any new or significantly changed script, mentally verify:

1. **Business rule + email-safety compliance** — Bodies follow BCC_PROPOSAL_RULES.md; no batch send without explicit `Y`; cold-outreach subjects don't say "Proposal"; cold outreach to GC targets does not pitch Plan Review.
2. **Logic correctness** — Loops terminate; edge cases handled (empty lists, missing fields, expired cookies).
3. **File safety** — Old-draft cleanup only targets known prefixes (`CW_*`, `Email_*`); never deletes `*-SENT.md` or non-temp files.

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
# Pipeline status — always run this first when asked "what's pending?"
python core_tools/work_log.py --status

# Inbox audit — pulls IMAP from admin@/ycao@ and produces 5-bucket report.
# Run this when work_log disagrees with reality (e.g. send_proposals.py
# does NOT write work_log status, so its "sent" state lives only in IMAP).
python core_tools/bcc_inbox_audit.py

# Lead scraping (Playwright)
python constructionwire_dc_leads.py
python buildingconnected_bid_scraper.py

# Proposal pipeline — three phases:
#   Phase 1 (phase1_extract): BC scrape → bc_current_lead.json
#   Phase 2 (phase2_generate_and_audit, max_loops=3): proposal_generator → internal audit gate
#   Phase 3: hand-off (Gemini-web verification removed; internal audit IS the QA gate)
python run_master_proposal_pipeline.py

# Approval monitor daemon (watches Pending_Approval/Outbound/ for *-OK rename)
python approval_monitor.py

# Telegram handoff (zero AI cost — requests only)
python core_tools/handoff_to_telegram.py

# Senior Architect (Gemini) — only when user explicitly asks
python core_tools/ask_senior.py <file> "<question>" --model gemini-2.5-flash
```

There is no `tests/` directory; `python -m pytest` will collect almost nothing.
Treat tests as ad-hoc — write a `test_<thing>.py` next to the module being changed
when you want a logic gate, but don't expect a project-wide suite.

## Phase 2 Dispatch (Mac → Windows over Tailscale) — LIVE

**Windows (`LAPTOP-GJ02LFQ7`) is the sole execution node.** It owns cookies,
`sent_log.json`, `Pending_Approval/Outbound/`, `work_log`, scraped data, and
all browser sessions. The Mac mini is a thin dispatch client — never touches
business state directly. This avoids the duplicate-send / lock-thrash class
of bug that motivated Phase 1's `active_operator` lock.

From the Mac, run any script via:
```bash
core_tools/bcc-remote.sh <script.py> [args...]
# e.g.
core_tools/bcc-remote.sh core_tools/work_log.py --status
core_tools/bcc-remote.sh daily_sender.py --dry-run
```
The wrapper SSHes into the Windows node (Tailscale magic-DNS + Windows
OpenSSH Server) and invokes Python there with the args quoted for PowerShell.
Tailscale SSH does NOT work to Windows targets — OpenSSH is doing the auth.

Phase 1's `core_tools/active_operator.py` (cross-machine cooperative lock at
`<bridge>/ACTIVE_OPERATOR.txt` — see core_tools/ index for bridge resolution) is still wrapped around every
write-side script (`send_*`, scrapers, form submissions) as a fallback —
do **not** remove it until Phase 2 has ≥1 week of stable operation.
Pattern in scripts:
```python
from core_tools.active_operator import operator_lock
with operator_lock(__file__):
    run_send_loop()
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

### Sender Script Families (read filenames carefully — they're not self-explanatory)

| Family | Scripts | What it sends | Attachment? |
|--------|---------|---------------|-------------|
| **Cold outreach** (uninvited) | `send_cw_outreach.py`, `send_cw_batch_*.py`, `send_to_telegram_review.py`, `send_carr_outreach.py`, `kcy_outreach.py` | Intro email — no proposal language, DC-only scope, 3-subject randomizer | NO PDF |
| **Formal proposal** (invited / interested) | `send_proposals.py`, `run_master_proposal_pipeline.py` | Email body + proposal `.docx` → user converts to PDF manually | YES PDF |
| **Follow-up** | `send_followup_proposals.py`, `send_cw_followups.py`, `auto_followup.py` | Reply against prior thread, default 4-day cadence | varies |
| **Daily orchestrator** | `daily_sender.py`, `drip_sender.py` | Wraps the above; gated by `active_operator` lock | — |

`send_to_telegram_review.py` is **cold outreach**, not a review tool — name is misleading.
`send_proposals.py` does **not** write `work_log` status — when checking "did we send X", run `core_tools/bcc_inbox_audit.py`, not `work_log --status`.

### Outreach State of Truth

`BCC_Outreach_Tracker.md` at the repo root is the canonical pipeline view across
cold sends / followups / replies. Read it before answering "did we contact X?"
or "what's the next followup?". Update it after every send, followup, or reply.

### Email Threading Limitation

`email_sender.py` does NOT currently set `In-Reply-To` / `References` headers.
Replies sent through it appear as fresh emails to Gmail/Outlook and break the
thread. Before writing any reply-flow code, extend the sender to accept and
emit those headers — don't paper over with quoted body alone.

## Critical Business Rules

### Email: Human Approval Required (No Exceptions)
Two approval paths coexist — pick one, don't bypass both:
1. **Synchronous** — display `Email content ready for [Contact]. Please review '[path]' and type 'Y' to send.` and block on terminal input.
2. **Async file-rename** — write draft to `Pending_Approval/Outbound/<name>.md`. Kyle renames to `<name>-OK.md` (mobile-friendly). `approval_monitor.py` watches the dir, sends, then renames to `<name>-SENT.md`.

Send from `admin@buildingcodeconsulting.com`, CC `ycao@`. Do NOT append signatures (auto-signatures enabled on both accounts).

### Gemini Web Cookie Gate (mandatory before any Gemini-web operation)
Before opening Gemini web, run `python check_gemini_cookie_expiry.py --check`. Exit code 1 → cookie missing/expired → run `start_chrome_for_gemini_login.bat`, ask Kyle to log in to gemini.google.com in that Chrome, then `python google_gemini_login_chrome.py` to save cookies. Don't skip this gate; stale cookies silently fail downstream.

### Inbox/ACTIVE_TASK.md Watch Pattern (Telegram → repo bridge)
When `Inbox/ACTIVE_TASK.md` mtime/content changes, that's Kyle pushing a task from Telegram (`/save`). Treat it as priority work: read the file, identify the project/client, execute, then write a confirmation to `Inbox/TASK_STATUS.md`.

### Proposals: Obey BCC_PROPOSAL_RULES.md
Before generating any proposal, read `BCC_PROPOSAL_RULES.md`. It contains: § 0 scraping selectors (BC Overview/Location), fee tiers ($295 large-volume → $375-400 one-time/complex), fee table row expansions (close-in/insulation/final phased + restaurant/interior-only rules), cold-vs-invited language rules, canonical credential bullets, forbidden phrases. Client name, contact, address, description, and fees must come from real BuildingConnected data — never placeholders. All text must be black.

### Scraping Rule Fixation
When a correct scraping method is found, immediately record it in `BCC_PROPOSAL_RULES.md` § 0. Do not just fix the code — update the rules file so the knowledge persists.

### Check Inbox: Consult Work Log First (then IMAP if it disagrees)
Before generating any proposal or drafting any email, run `python core_tools/work_log.py --status`. Skip projects where proposal is done, or email sent and follow-up not yet due. Default follow-up interval: 4 days.

If work_log seems wrong (especially for formal-proposal sends, which don't update it), reconcile against IMAP via `python core_tools/bcc_inbox_audit.py` before acting. The `2026-04-22 duplicate-send incident` is the precedent — never re-run a send script "just to verify."

### Service Territory (current — updated 2026-04-22)
- **Inspection (3PI)**: DC + Fairfax County VA = full 5-discipline scope. PG County MD pending Kyle 开通. Montgomery County MD is **OUT** (their program only authorizes B+M, not full 5-discipline). Arlington / Alexandria / other NoVA = ask Kyle per project.
- **Plan Review**: nationwide / global
- **Code Consulting**: up to Baltimore (north), Norfolk (south), ~2.5 hr from Northern VA

### Anti-Spam Subject Randomizer (per `.cursorrules`)
For every cold-outreach lead, generate **3 distinct subject lines** (Plan Review angle, 24-hr Inspection angle, project-specific angle) and **randomly pick 1**. Note the chosen subject + the two alternatives at the top of the draft file. Do not reuse the same template across leads.

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

## Plan Review Wrap-Up Packages

One-shot trigger: Kyle pastes 1+ Google Sheet URLs + says "wrap up" → call Drive MCP `download_file_content` per URL → save JSON tool-result to `_drive_cache/<file_id>.json` → run:

```bash
python wrapup_from_sheets.py "<sheet_url_1>" [...]            # preview, halts for Y
python wrapup_from_sheets.py "<sheet_url_1>" [...] --send     # after Y
```

Full 17-step workflow + 5-doc package detail: see `Wrap up/CLAUDE.md`. Reference example: `../Projects/Plan Review from Jessica Liang/1345-1347 Conn Ave Karaoke Store FA PR/1345 Conn Ave FA/Wrap up/`.

## Fairfax Inspection Reports

Reference implementation: `fill_3303_lockheed_reports.py`. Pipeline: fill AcroForm → chunk comments → ASCII-safe → fitz-stamp `E-Sig.jpg` on "Signature:" line via `search_for` → flatten 250 DPI → submit via `fairfax_3pi_submit.py`. Owner/permit metadata lives in each project's `project_info.md` — extract FIRST on any new project. Cap routine jobs at ~5-7 tool calls; no re-reading PDFs after every edit, no dry-runs of proven workflows.
