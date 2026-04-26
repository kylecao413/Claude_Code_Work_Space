# BCC/KCY Daily Command Center

This folder is the daily operating dashboard for Building Code Consulting LLC
and KCY Engineering Code Consulting, LLC.

The first version is intentionally simple and zero-cost:

- no AI calls
- no browser automation
- no email sending
- no county form submission
- no credential access beyond reading local operational files

Run:

```powershell
python core_tools/daily_command_center.py
```

Output:

```text
Command_Center/Daily_Command_Center_YYYY-MM-DD.md
```

## Operating Model

Codex is the general manager:

- reads the daily brief
- identifies what Kyle needs to decide
- delegates narrow implementation tasks to Claude Code
- asks Gemini Pro web only for deep research, screenshots, long documents, or second opinions
- keeps humans in the loop for all outbound email, county submissions, filings, and credential changes

Claude Code is the executor:

- bounded code edits
- local script fixes
- batch draft generation
- tests and mechanical refactors

Gemini Pro web is the senior researcher/reviewer:

- deep web research
- large document analysis
- webpage/sidebar research
- multimodal review

## Non-Negotiables

- Do not store ChatGPT, Google, Claude, or Gemini account passwords in `.env`.
- Use browser profiles, OAuth, or scoped API keys instead of account passwords.
- No send script runs without explicit Kyle approval.
- No Fairfax/County/State submission without `--dry-run` first and Kyle approval.
- No secret values are copied into reports.
