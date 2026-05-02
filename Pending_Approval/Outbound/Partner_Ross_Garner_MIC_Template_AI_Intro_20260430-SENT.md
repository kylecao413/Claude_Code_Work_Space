# Partner Email — Ross Garner (MIC template share + Claude Code intro)

**To:** louis@americanplanreview.com
**CC:** ycao@buildingcodeconsulting.com
**From:** admin@buildingcodeconsulting.com
**Subject:** BCC Master Inspection Contract template + intro to my AI agent (Claude Code)

**Attachments:**
- `Master Contract And ATP/BCC Third Party Code Compliance Inspection Service Master Proposal Template.docx` (the canonical MIC template — sent as .docx so you can copy and customize per client)

---

Hi Ross,

Quick share for you, plus an intro to the AI agent I have been using to scale the BCC operation. I figured you would want both of these as you start spinning up the marketing side and getting Claude Code wired in.

**1. The Master Inspection Contract template (attached)**

This is the canonical contract I use whenever a contractor wants a long-term TPI relationship with BCC instead of a per-project proposal. Two pieces:

- **MIC (Master Inspection Contract)** — one signed per client, one-year term, auto-renews annually unless either side gives 30-day notice. Article 4 holds the standard fee schedule (flexible — single-rate, or two-tier $X single-trade / $Y combination, depending on client). Article 5 carries the standard T&Cs (payment, 30-day pay window, liability cap = total fees paid, Maryland governing law, etc.).
- **ATP (Authorization to Proceed)** — a 1-pager issued per project under the parent MIC. Names the project, address, permit, disciplines, visit estimate. Pulls all its terms from the MIC by reference, so it is a fast sign-and-start.

The architecture pays off the moment a contractor pulls a second permit — you negotiate the relationship once, then every future job moves at permit speed. Numbering is sequential globally: `MIC-YYYY-NNN` and `ATP-YYYY-NNN`. The template you have shows MIC-2026-005 as a placeholder; replace it with your next available number when you customize for a new client.

I have already issued these:
- MIC-2026-001 — Jerald Brown
- MIC-2026-005 — Alper Akan
- MIC-2026-006 — Team VP Construction (just sent today)
- ATP-2026-001 — Team VP / 5118 8th St NW UG Plumbing

Feel free to use the same template + numbering scheme for your American Plan Review clients if it fits — or fork it for your own contract conventions.

**2. About Claude Code (the CLI you just downloaded)**

Claude Code is Anthropic's command-line agent. It is not a chat-only assistant — it reads your files, writes code, runs terminal commands, searches the web, sends emails (with your approval), and operates tools you give it access to. I have been running it inside the BCC `Business Automation/` repo for several months.

What it does for me on the BCC side, day-to-day:

- **Lead scraping** — Playwright pipelines pull DC project leads from ConstructionWire and BuildingConnected automatically.
- **Proposal + contract generation** — generates the Master Inspection Contract you have attached, plus per-project proposals and ATPs, all from Word templates (zero AI cost — local docx fill).
- **Email drafting** — drafts cold outreach, follow-ups, and proposal emails. Stages every draft in a `Pending_Approval/Outbound/` folder, never sends without my explicit approval (a `-OK.md` rename triggers send).
- **Inspection reports** — fills Fairfax and DC inspection PDFs, e-stamps the signature, submits to county portals.
- **Persistent memory** — keeps a memory file across sessions so I do not have to re-explain BCC business rules every time I open a new conversation.

What it can do for you on the marketing / sales side specifically:

- **Cold outreach at scale** — give it a target list (architects, GCs, owners), it researches each contact, drafts a personalized outreach email per target, stages them all for your review. Follows anti-spam rules: 3 randomized subject lines per lead, no template repetition.
- **Contact research** — deep web search on a company or person, finds decision-makers, surfaces recent project announcements, writes you a one-pager.
- **Marketing collateral** — capability statements, follow-up sequences, LinkedIn drafts, proposals, all on demand.
- **Gmail / Calendar / Drive** — built-in MCP integrations to search your inbox, schedule meetings, pull files from Drive.
- **Trackers** — Markdown-based CRM trackers like our `BCC_Outreach_Tracker.md` (one source of truth for who has been contacted, who has replied, who is due for follow-up).
- **Recurring automations** — `/loop` or `/schedule` commands to run a task on a cadence ("every Monday, pull last week's replies and triage them").

To get rolling:

1. Open Claude Code in any directory and type `/help` to see commands.
2. `/init` scans your repo and writes a `CLAUDE.md` file with project conventions — that becomes the agent's standing instructions for that codebase.
3. Talk to it in plain English. It works best with context (what you are trying to do and why), not narrow instructions.
4. If you want to see how I have it set up, peek at `Building Code Consulting/Business Automation/CLAUDE.md` and `MEMORY.md` — those are the agent's standing instructions and persistent memory for the BCC repo. Good reference for how to structure your own.

Happy to jump on a screen-share whenever you want a walkthrough — I can show you the BCC pipeline live and we can wire up the equivalent for American Plan Review. Excited to have you on the AI side of the operation.
