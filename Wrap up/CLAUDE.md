# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this folder is

**Template / master folder for Plan Review Wrap-Up packages.** Holds the reusable `Large Stamp Template.docx` plus (for convenience) a copy of the most recent example wrap-up. Actual per-project wrap-up packages live under each project's own `/Wrap up` subfolder, e.g.:

`../Projects/Plan Review from Jessica Liang/1345-1347 Conn Ave Karaoke Store FA PR/1345 Conn Ave FA/Wrap up/`

That example folder is the canonical completed reference and has its own detailed `CLAUDE.md`.

## The 5-document wrap-up package

Every DC DOB Third Party Plan Review project ends with this 5-doc submittal to DOB. Filename pattern: `<project address> <discipline abbrev> <doc type>`.

| # | Doc | Source | What changes per project |
|---|-----|--------|--------------------------|
| 1 | `<addr> <disc> PR NOI for DOB.pdf` | Downloaded from the DOB NOI approval email. **Extract the `TPR######-###` approval number** from it (e.g. `TPR200000-587`). | N/A — downloaded as-is. |
| 2 | `<addr> <disc> Deficiency Report.xlsx - Deficiency Report.pdf` | Generated from the project's `.xlsx` deficiency report: select filled content-table print area in Excel → Print as PDF. | N/A — PDF export of xlsx. |
| 3 | `<addr> <disc> Plan Review Approval Certificate and Report.pdf` | DOB form template. | DOB Notification Approval Number (the TPR from Doc #1), Date, Project Name, Project Address, discipline checkbox, discipline row in the table (discipline / Date of Code Deficiency Report / Date Corrections Verified / Date of Report Reflecting Approval), signature date, "Professional-in-Charge of ___ discipline" blank. |
| 4 | `<addr> <disc> Plan Review Certification Letter.pdf` (from `.docx`) | BCC letterhead template. | Issuing date, project address (Subject + salutation), disciplines bullet list. |
| 5 | `Large Stamp for <addr> <disc> review.pdf` | `Large Stamp Template.docx` in THIS folder. | Project address, discipline + signature + date row(s). |

## Critical rules

**TPR approval number** — the `TPR######-###` on Doc #1 (example: `TPR200000-587`) goes into the "DOB Notification Approval Number" field on Doc #3. Do NOT confuse with BCC's **Agency Approval ID `TPR-05012025`** which is constant across all projects.

**Date relationship on Doc #3** — *Date Corrections Verified* and *Date of Report Reflecting Approval* are usually the **same day or 1 day apart**. The signature date at the bottom must match *Date of Report Reflecting Approval*.

**Fixed fields (never change across projects):**
- Doc #3: Name of Agency `Building Code Consulting`; Agency Approval ID `TPR-05012025`; PE/MCP Number `PE920502`; Print Full Name and Title `Yue Cao Professional in Charge`.
- Doc #4: Letterhead `13950 Route 50 #3033, Chantilly, VA 20151, (571) 365-6937`; Addressed to `Department of Buildings (DOB), 1101 4th Street SW, Washington D.C., Attention: Mayda Colon`; Signed `Yue Cao, Building Code Consulting, Professional-In-Charge, TPR-05012025`.
- Doc #5: Construction Code Verified list is standard boilerplate in the template (2017 DCMR 12A/12E/12F/12C/12H/12I/12K/12I, 2013 NFPA 13/14/72).

**Discipline naming (Fire Protection example):** filename uses `FA`; Doc #3 checkbox is `Fire`, table row is `Fire Protection`, "___ discipline" blank is `Fire(electrical) & Sprinkler`; Docs #4 and #5 write `Fire Protection` / `Fire Protection System`.

**Signatures** — applied by Yue Cao on Doc #3 and Doc #5 after fields are filled. Do not fabricate.

## When asked to prepare a new wrap-up package

1. Confirm the five inputs: project address, project name, discipline(s), NOI approval PDF (to extract TPR number), deficiency report `.xlsx`, and the three key dates.
2. Produce the 5 output files matching the naming pattern and field conventions above.
3. Place them in the project's own `Wrap up/` subfolder (not this template folder).
4. Ask the user to apply signatures on Doc #3 and Doc #5 before DOB submission.
