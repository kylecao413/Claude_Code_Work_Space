# BCC/KCY Manager Playbook — Claude Code Orchestration

This playbook defines how a Claude Code session operates as **manager** for
BCC/KCY daily operations.

**Current primary mechanism:** the regular `Agent` tool (Explore / Plan /
general-purpose / custom `.claude/agents/` subagents). This is what actually
works in Claude Code 2.1.119 today — parallel delegation, bounded scope,
results returned to the lead for review.

**Secondary / future:** Agent Teams (`TeamCreate` / `SendMessage` /
`TaskCreate`-on-shared-list). The substrate is live as of 2.1.119 and the
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` flag is enabled in
`.claude/settings.local.json`, **but** the spawn path (Agent tool accepting
`team_name` + `name` to enroll a teammate) is not wired up in the 2.1.119
tool-use surface — smoke test 2026-04-24 confirmed teammates do not actually
join the team when spawned via `Agent`. Revisit when a future Claude Code
release either extends the `Agent` tool schema with those params or adds a
dedicated spawn tool. See §13 for the smoke test record.

Carries forward Codex's original operating model (`Command_Center/README.md`).

**Who reads this:** The Claude Code session that will act as manager. Load this
playbook at session start (see §2). Do NOT pre-author team configs by hand —
if/when Agent Teams spawn works, the system generates them.

---

## 1. Role Mapping (Codex design → Today's Reality)

| Codex original role | Today's equivalent (regular Agent tool) | Notes |
|---|---|---|
| **Codex** = general manager | **This Claude Code session** = the manager | Reads brief, plans, delegates, reviews, reports to Kyle |
| **Claude Code** = executor | **Sub-agents via `Agent` tool**: Explore (read-only research), Plan (read-only architecture), general-purpose (full tools), or custom agents from `.claude/agents/` | One `Agent` call = one bounded task, result returned to manager for review. Parallel delegation via multiple Agent calls in one message |
| **Gemini Pro web** = senior researcher | **Out of band — Kyle's browser** | Manager requests manually when deep Gemini web research warranted |
| `ask_senior.py` (Gemini API) | **Tool, not a role** | Manager calls directly when structured second opinion needed; follows cost rules in CLAUDE.md |
| Daily Command Center brief | **Unchanged** | `Command_Center/Daily_Command_Center_YYYY-MM-DD.md` — first read of every session |
| Pending_Approval / Telegram gate | **Unchanged** | Hard human-in-loop gate before any send / submit |

### Future (when Agent Teams spawn works)
| Codex original role | Agent Teams target | Notes |
|---|---|---|
| **Codex** = general manager | **Team lead** (this session) | Same as above, additionally coordinates team shared task list |
| **Claude Code** = executor | **Persistent teammate Claude Code instance(s)** | Each teammate own context window, peer-to-peer messaging, shared task list. Higher token cost but lower overhead for long parallel work blocks |

---

## 2. Manager Session Opening Protocol

Every time a new `claude` session starts with intent to manage, run in order:

1. **Check today's brief exists**
   ```bash
   ls Command_Center/Daily_Command_Center_$(date +%Y-%m-%d).md
   ```
   Missing → `python core_tools/daily_command_center.py`, then read it.

2. **Read the brief end-to-end** — it is the day's source of truth for:
   - Outstanding drafts in `Pending_Approval/Outbound/`
   - New BC bid board items needing triage
   - Fairfax submissions queued
   - PE/KCY licensing pipeline state
   - Recent sent-log tail (to avoid re-send)

3. **Read `CLAUDE.md` + `MEMORY.md` + `BCC_PROPOSAL_RULES.md`** — hard rules
   (fee tiers, service territory, email non-negotiables, DC Gov exclusion, etc.).

4. **Decide delegation strategy** — see §4. Default: solo or regular `Agent`
   sub-agents. Agent Teams spawn is not functional in 2.1.119 (see §13).

5. **Report a short plan to Kyle** before delegating — 3–6 bullets:
   what work is queued, how it will be split across sub-agents, expected
   deliverables.

---

## 3. Enablement (one-time setup — flag kept live for future activation)

Reference: <https://code.claude.com/docs/en/agent-teams>

### 3a. Version check
Agent Teams infrastructure requires **Claude Code ≥ 2.1.32**. Verified on
2026-04-24 at version **2.1.119** — TeamCreate/TeamDelete/SendMessage tools
work; Agent-tool spawn path does not (see §13).
```bash
claude --version
```

### 3b. Settings flag
Add to `.claude/settings.local.json` (project-scope, preferred) or
`~/.claude/settings.json` (user-scope):
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```
Value is the **string** `"1"`, not boolean `true`.

### 3c. Teammate display mode
Default `in-process` (all teammates share main terminal; `Shift+Down` to cycle)
works on Windows Terminal and is fine for BCC.

Optional `tmux` mode (split panes) requires tmux/iTerm2 — not needed on Windows.
Set in `~/.claude.json` if later desired:
```json
{ "teammateMode": "in-process" }
```

### 3d. Restart
After adding the flag, restart `claude` so the env var is in scope. The flag
is already set; leave it on so future Claude Code releases that fix the spawn
path auto-light-up this session.

---

## 4. Delegation Strategy (what's actually available today)

Default: **solo or regular `Agent` sub-agents**. Agent Teams spawn not
functional in 2.1.119.

| Situation | Approach (today) |
|---|---|
| 1 proposal to generate, rules clear | **Solo** — manager runs `proposal_generator.py` |
| 1 scraper bug with known symptom | **Solo** — `/bcc-investigate` skill |
| 1 outbound email review | **Solo** — `/bcc-review` skill |
| 5–10 BC drafts to generate in parallel | **Parallel `Agent` calls**: spawn N general-purpose sub-agents in one message, one per project; manager collects results and reviews |
| Scraper broken AND proposal batch AND email drafting all queued | **Parallel `Agent` calls**: one Explore (investigate scraper), one general-purpose (batch proposals), one general-purpose (email drafts); manager sequences by priority |
| Multi-angle strategic question (e.g., FL vs TX expansion) | **`/bcc-strategy` skill** solo, OR one Plan sub-agent |
| Quick look-up or one-file change | **Solo** — do it directly; sub-agent overhead not justified |

### Key differences to remember
- **Regular `Agent` tool** (today's path): bounded, one-shot task → result
  returned to manager → manager reviews → next step. Lower token cost.
  No peer-to-peer between sub-agents; all coordination goes through manager.
- **Agent Teams** (future path when spawn works): independent peers with
  shared task list and peer-to-peer messaging; higher cost; good for long
  parallel work blocks where peers challenge each other.

### Parallel `Agent` calls — how
Multiple `Agent` tool calls in a **single assistant message** run in parallel
and return to the manager together. Use this when 2+ genuinely independent
tasks are queued. Do NOT chain them serially if they don't need to be
sequential.

---

## 5. BCC Custom Sub-agent Templates (reusable roles)

Custom agents live in `.claude/agents/` and are invoked via the regular
`Agent` tool with `subagent_type: <agent-name>`. The same definitions will
work as Agent Teams teammates once spawn is functional.

Proposed initial roster (create on demand, don't build all at once):

| Agent name | Purpose | Key tools to allowlist |
|---|---|---|
| `bcc-proposal-generator` | Run `proposal_generator.py` for one project; obey `BCC_PROPOSAL_RULES.md`; write draft to `Pending_Approval/Outbound/` | Bash, Read, Write, Edit |
| `bcc-email-drafter` | Draft one outbound email (.md + .docx) per project; obey email rules in MEMORY.md | Read, Write, Edit |
| `bcc-reviewer` | Pre-send review against rules; mirrors `/bcc-review` skill | Read, Grep, Bash |
| `bcc-scraper-investigator` | Root-cause scraper failure; mirrors `/bcc-investigate` skill; NO auto-fix | Read, Grep, Bash |
| `bcc-fairfax-submitter` | Dry-run only; prepares `fairfax_3pi_submit.py` invocation; never submits without Kyle Y | Bash, Read |

Do not create these proactively. Only scaffold when a real workflow demands
the role twice.

---

## 6. Review Loop (non-negotiable)

When a sub-agent returns work:

1. **Manager pulls the artifact** — diff, draft file, or tool output. Do not
   trust the sub-agent's self-report — verify the actual file/diff exists.
2. **Verify against hard rules**:
   - Proposals → `BCC_PROPOSAL_RULES.md` + `MEMORY.md` fee tables + service territory + credential language
   - Emails → MEMORY.md § Email Rules (no signature, no ellipses, billing disclaimer, BTW plan review note)
   - Scraper fixes → the iron law: no fix without verified root cause; update `BCC_PROPOSAL_RULES.md § 0` if a selector changed
3. **Kick back if fails** — spawn a follow-up `Agent` call with the specific
   rule violated and the exact fix required. Do NOT silently fix the sub-agent's
   work without recording why — the next sub-agent will repeat the mistake.
4. **Move to `Pending_Approval/Outbound/`** only after the artifact passes.
5. **Summarize to Kyle** with file paths, then wait for Y/approval.

---

## 7. Non-Negotiables (inherited from Codex model, still apply)

1. No account passwords (ChatGPT / Google / Claude / Gemini) in `.env`. Use
   browser profiles, OAuth, or scoped API keys.
2. No send script (`email_sender.py`, `send_proposals.py`, `send_cw_outreach.py`,
   `send_to_telegram_review.py`, daily_sender.py) runs without explicit Kyle
   approval (`Y` or "Proceed with sending").
3. No Fairfax / county / state submission without `--dry-run` first AND Kyle's
   explicit go-ahead.
4. Never copy secret values into `Command_Center/` reports, playbooks, memory,
   Telegram messages, or teammate prompts.
5. Never re-run a send script to "check results" — re-read sent log instead
   (see `MEMORY.md` § Never Re-run Send Scripts, 2026-04-22 incident).
6. Service territory: DC + Fairfax only for full 5-discipline TPI; Montgomery
   OUT; PG pending. Plan Review & Code Consulting nationwide.
7. DC Government agencies are never cold-emailed (they inspect in-house).

---

## 8. Known Caveats (plan around these)

### Today (regular `Agent` tool)
- **Sub-agent results are one-shot.** Each `Agent` call is a single
  request/response round. No long-lived teammate state. For multi-step work,
  manager must re-spawn with the next step's context.
- **Sub-agents can't talk to each other.** All coordination routes through
  the manager. Parallel `Agent` calls run independently; their findings are
  only unified when they return to the manager.
- **No file locking.** If two parallel sub-agents edit the same file, one
  write wins. Manager must partition work so no two sub-agents touch the same
  file in the same assistant message.

### Future (when Agent Teams spawn works — from official docs)
- **No session resumption for in-process teammates.** `/resume` and `/rewind`
  restore only the lead. Don't stand up a team spanning > 1 session.
- **Task status can lag.** Teammates sometimes fail to mark tasks completed.
- **Lead is fixed.** No promoting a teammate to lead mid-stream.
- **No nested teams.** Teammates cannot spawn their own teammates.
- **One team per lead.** Tear down before starting another.
- **Permissions at spawn time.** Teammates inherit lead's permission mode.
- **Shutdown is slow.** Teammates finish current tool call before exiting.

---

## 9. Quality Gates via Hooks (optional, add when needed)

Claude Code supports three Agent-Teams-specific hooks (see
<https://code.claude.com/docs/en/hooks>). For BCC, the highest-value gates:

- `TaskCompleted` — exit code 2 to prevent marking complete. **Use case:**
  block marking a proposal task "done" if the draft hasn't been written to
  `Pending_Approval/Outbound/`. Hook script checks file exists with expected
  naming convention.
- `TaskCreated` — exit code 2 to reject. **Use case:** reject tasks that
  mention forbidden scope (Montgomery County inspection, DC Gov cold email,
  plan review pitch inside an inspection proposal .docx).
- `TeammateIdle` — exit code 2 to keep working. **Use case:** refuse to let
  a teammate idle until it has produced both the .md draft AND the .docx draft
  for a given project.

Do not add hooks preemptively. Add when a specific failure mode has occurred
twice and we want to harden against it.

---

## 10. Minimum Working Example (today — regular `Agent` tool)

Kyle's prompt to manager:
```
I've read today's Command_Center brief. 3 BC proposals to draft:
AIA Headquarters (Turner), GPO NARA 4th Floor (Capital Trades),
Panda Express (Parkway). Draft all three, then review each against
BCC_PROPOSAL_RULES.md, then summarize to me for Y-approval.
```

Manager executes (in a single assistant message):
1. **Parallel**: 3 `Agent` calls with `subagent_type: general-purpose` (or
   `bcc-proposal-generator` if defined) — one per project. Each writes a
   draft to `Pending_Approval/Outbound/` and returns the file path.
2. **After all 3 return**: 1 `Agent` call with `subagent_type: Explore` (or
   `bcc-reviewer`) given all 3 paths, plus `BCC_PROPOSAL_RULES.md` + relevant
   MEMORY.md sections — returns a pass/fail list with specific rule
   violations if any.
3. **Manager**: if any fail, re-spawn generator for that one with the rule
   violation as context. If all pass, summarize paths + prices + key rule
   checks to Kyle.
4. **Kyle**: Y or kickback.

---

## 11. When to Stay Solo (no sub-agents)

If any of these are true, do NOT delegate — just do it in the manager session:

- Only 1 small artifact to produce (sub-agent overhead > task size)
- Work requires iterative tight-loop editing of the same file
- Token budget tight this week
- Kyle said "just do it" or asked for a quick turnaround
- Task inherently sequential with no parallelism to exploit

---

## 12. Change Log

- **2026-04-24** — Initial playbook. Derived from `Command_Center/README.md`
  (Codex-era manager design) + official Agent Teams documentation
  (<https://code.claude.com/docs/en/agent-teams>).
- **2026-04-24 (later)** — Revised after smoke test (§13). Agent Teams spawn
  path not functional in 2.1.119; primary mechanism is now regular `Agent`
  tool sub-agents. Agent Teams retained as future target with flag kept live.

---

## 13. Smoke Test Record (2026-04-24)

**Environment:** Claude Code 2.1.119 on Windows, interactive session,
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.local.json`.

**Steps executed:**
1. `TeamCreate(team_name="bcc-smoketest-01", agent_type="manager")` → ✅
   team directory `~/.claude/teams/bcc-smoketest-01/` + task directory created;
   config.json shows lead only.
2. Called `Agent` tool with `subagent_type: Explore` + prompt instructing the
   sub-agent to "be teammate 'reader' in team bcc-smoketest-01" and report
   via `SendMessage` → sub-agent returned "Done. Going idle." but:
   - **config.json still showed only team-lead in members** (no teammate
     enrolled)
   - **no auto-delivered teammate→lead message** arrived
3. Second attempt with explicit prompt framing → same result.
4. `TeamDelete()` → ✅ clean removal.

**Finding:** The `Agent` tool schema surfaced to this session has
`additionalProperties: false` and does not accept `team_name` / `name`
parameters that TeamCreate's doc says are required to enroll a teammate.
Sub-agents spawned via `Agent` complete normally but never join the team's
`members` array and cannot use `SendMessage` automatic delivery.

**Conclusion:** TeamCreate / SendMessage / TeamDelete / shared-task-list
infrastructure is wired up in 2.1.119, but the **spawn path** (Agent tool
enrolling a sub-agent as a teammate) is not. Revisit when a future Claude
Code release either (a) extends `Agent` tool schema with `team_name` + `name`
params, or (b) introduces a dedicated spawn tool (`TeammateSpawn` or similar).

**Until then:** use regular `Agent` tool sub-agents as described in §4 and
§10. The flag stays live so a future release auto-activates the spawn path.
