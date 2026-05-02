# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚡ Quick Start — when Kyle says "wrap up" with sheet URLs

If Kyle pastes 1+ Google Spreadsheet URLs and says **"wrap up"** (any language, any phrasing — "做 wrap up", "wrapup", "wrap it up", "submit", "deliver"), invoke the bootstrap script:

```bash
# For each URL, FIRST call Drive MCP and cache the JSON tool-result, then run:
python wrapup_from_sheets.py "<URL1>" ["<URL2>" ...]                # halts at preview, requires Y to proceed
python wrapup_from_sheets.py "<URL1>" ["<URL2>" ...] --send          # only after Kyle says Y
```

The script does the entire 17-step chain end to end:
1. Parse URLs → file IDs
2. Download sheets via Drive MCP → cache to `_drive_cache/<file_id>.json` (Claude must invoke MCP first; script unwraps the cached JSON)
3. Read sheet metadata → project address + discipline tag
4. Locate project folder under `Projects/<Client>/<Project>` by address match
5. Locate `Approved_*NOI*signed*.pdf` (newest mtime)
6. Parse NOI → TPR # + DOB acceptance date + project name
7. Derive dates: deficiency = NOI acceptance date; verified = approval = today
8. Resolve discipline strings (Doc #3 blank, letter list, large-stamp rows)
9. Look up recipient in `BCC_Outreach_Tracker.md` (or `--to NAME EMAIL`)
10. Generate Doc #1 (NOI copy), Doc #2 (per-discipline xlsx → PDF print), Doc #3 (AcroForm fill on Guide Manual page 61), Doc #4 (cert letter docx → PDF), Doc #5 (large stamp docx → PDF)
11. **Flatten ALL** PDFs at 250 DPI (universal DOB submittal rule)
12. Self-review every PDF (size + widget count + must-have-text strings)
13. Save draft email to `Pending_Approval/Outbound/<addr>_Wrapup_Draft.md`
14. Print preview to console
15. **Halt and wait for Kyle's "Y"** unless `--send`
16. SMTP send via `email_sender.send_from_admin_with_attachments`
17. Rename draft to `-SENT.md` for audit

Each step is a function in `wrapup_from_sheets.py` that fails loudly with a clear "what to check" message — no silent defaults.

**Required Claude steps before running**: download each sheet via the Drive MCP (`mcp__claude_ai_Google_Drive__download_file_content`, `exportMimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) and ensure the JSON tool-result is saved at `Business Automation/_drive_cache/<file_id>.json`. The script's step 2 expects this cache.

## What this folder is

**Template / master folder for Plan Review Wrap-Up packages.** Holds the reusable `Large Stamp Template.docx` plus (for convenience) a copy of the most recent example wrap-up. Actual per-project wrap-up packages live under each project's own `/Wrap up` subfolder, e.g.:

`../Projects/Plan Review from Jessica Liang/1345-1347 Conn Ave Karaoke Store FA PR/1345 Conn Ave FA/Wrap up/`

That example folder is the canonical completed reference and has its own detailed `CLAUDE.md`.

## The 5-document wrap-up package

Every DC DOB Third Party Plan Review project ends with this 5-doc submittal to DOB. Filename pattern: `<project address> <discipline abbrev> <doc type>`.

| # | Doc | Source | What changes per project |
|---|-----|--------|--------------------------|
| 1 | `Approved_<addr>_..._signed.pdf` (preserve original filename) | The DOB-stamped approved NOI in the project folder. **Just `shutil.copy2` it into Wrap up/ as-is — do not rename, do not regenerate.** | N/A. |
| 2 | `<addr> <DISC> Plan Review Deficiency Report.pdf` (one per discipline) | **Google Spreadsheet Kyle shares — NOT local `.xlsx`** (those are blank templates). Recipe: Download Sheet as `.xlsx` → open in Excel → manually select filled rows → File → Print → **"Print Selection" + "Narrow Margins" + "Fit All Columns on One Page"** → printer = **"Microsoft Print to PDF"** → save into `Wrap up/`. Google Sheets itself cannot print a selected area. | Required deliverable. **Open the PDF and confirm real deficiency text** before declaring done — never ship a blank template (failure mode of 2026-04-28). |
| 3 | `<addr> <disc> Plan Review Approval Certificate and Report.pdf` | **AcroForm PDF on page 61 of `PLAN REVIEW PROJECT DOC TEMPLATE/Third-Party_Program_Procedure_Manual 5.15.2023 seal.pdf`.** Extract that single page via `fitz.insert_pdf(..., from_page=60, to_page=60)` and fill widgets (see field names below). **Never recreate the form in Word.** | DOB Notification Approval Number, Date, Project Name, Project Address, discipline checkbox, discipline rows + 3 dates each, signature date, "Professional-in-Charge of ___ discipline" blank. |
| 4 | `<addr> Plan Review Certification Letter.pdf` (from `.docx`) | BCC letterhead template. | Issuing date, project address (Subject + salutation), disciplines bullet list — **list `Fire Protection System`, `Sprinkler System`, `Fire Alarm System` as separate lines** (DOB officers need it spelled out). |
| 5 | `Large Stamp for <addr> <disc> review.pdf` | `Large Stamp Template.docx` in THIS folder. **Middle column of the nested 2×3 table contains an EMBEDDED SIGNATURE IMAGE of Yue. Never `cell.text = ...` on it — that wipes the image.** Update labels and dates by editing only text-run text on runs that do NOT contain `<w:drawing>`. Detect drawing runs by `r._r.find(qn("w:drawing"))`, not by namespace-string search. | Project address line; date column for each discipline row. |

## Critical rules

**TPR approval number** — the `TPR######-###` on Doc #1 (example: `TPR200000-587`) goes into the "DOB Notification Approval Number" field on Doc #3. Do NOT confuse with BCC's **Agency Approval ID `TPR-05012025`** which is constant across all projects.

**Doc #3 AcroForm field names** (from page 61 of the Guide Manual): `fill_1` = TPR; `Date`, `Permit Number`, `Project Name_2`, `Project Address_2`; checkboxes `Mechanical_2`/`Plumbing_2`/`Electrical_2`/`Construcon`/`Elevators`/`Fire_2`; rows `Plan Review DisciplineRow1`..`Row7` with date triplets `fill_15`/`fill_16`/`fill_17` (row 1), `fill_19`/`fill_20`/`fill_21` (row 2), etc.; `SIGNATURE_3` (leave blank for Yue), `day of` (= "<Month> <day>th"), `20` (= 2-digit year), `Print Full Name and Title`, `ProfessionalinCharge of Third Party Plan Review Agency for`, `Name of Agency`, `Agency Approval ID Number`, `Professional EngineerArchitect or MCP Number`.

**Date relationship on Doc #3** — *Date Corrections Verified* and *Date of Report Reflecting Approval* are usually the **same day or 1 day apart**. The signature date at the bottom must match *Date of Report Reflecting Approval*.

**Fixed fields (never change across projects):**
- Doc #3: Name of Agency `Building Code Consulting`; Agency Approval ID `TPR-05012025`; PE/MCP Number `PE920502`; Print Full Name and Title `Yue Cao Professional in Charge`.
- Doc #4: Letterhead `13950 Route 50 #3033, Chantilly, VA 20151, (571) 365-6937`; Addressed to `Department of Buildings (DOB), 1101 4th Street SW, Washington D.C., Attention: Mayda Colon`; Signed `Yue Cao, Building Code Consulting, Professional-In-Charge, TPR-05012025`.
- Doc #5: Construction Code Verified list is standard boilerplate in the template (2017 DCMR 12A/12E/12F/12C/12H/12I/12K/12I, 2013 NFPA 13/14/72).

**Discipline naming (Fire Protection example):** filename uses `FA`; Doc #3 checkbox is `Fire`, table row is `Fire Protection`, "___ discipline" blank is `Fire(electrical) & Sprinkler`; Docs #4 and #5 write `Fire Protection` / `Fire Protection System`.

**Signatures** — applied by Yue Cao on Doc #3 and Doc #5 after fields are filled. Do not fabricate. Note: the Guide Manual page-61 template's `SIGNATURE_3` widget already carries Yue's signature image in its appearance stream — when you fill the form and flatten, the signature bakes in automatically. Don't claim "missing signature" based on `page.get_text()` alone (text-extract doesn't see signature images); render to PNG (`page.get_pixmap(dpi=144)`) and inspect visually.

**Universal flatten rule (ALL submittal PDFs)** — every PDF leaving BCC for a DOB / county / city / AHJ submittal MUST be flattened (non-editable). No AcroForm widgets, no annotations, no editable layers. Apply as the **last** step before email: rasterize each page at 250 DPI, rebuild as a new PDF. Reference impl: `Business Automation/flatten_wrapup_pdfs.py`. Verify with `len(list(page.widgets() or []))` == 0. Doc #3 should drop from 47 widgets → 0 after flatten.

## Master template / process source

`C:\Users\Kyle Cao\DC Business\Building Code Consulting\PLAN REVIEW PROJECT DOC TEMPLATE\` is the master folder for all DC DOB Third-Party Plan Review process docs. Discipline-specific modules live as subfolders, e.g. `Fire Protection Shop Drawing Plan Review Module\` (workflow, sprinkler/FA checklists, code reference, required-docs list, report template, common findings). The wrap-up process below uses outputs from those modules — the deficiency-report `.xlsx` is produced by the discipline review, not generated here.

## Approved NOI auto-discovery

The "approved NOI" (Doc #1 source — supplies the TPR number) lives **inside the project folder** as the **latest signed NOI**, often renamed with an `Approved_` prefix (e.g. `Approved_1522_Rhode_Island_Ave_NE_SPK__FA_PR_NOI_signed.pdf`). To confirm: open it and check the **FOR OFFICIAL USE ONLY** box on the last page — it must show STAFF NAME, SIGNATURE, TITLE, DATE, and **NOTICE OF APPROVAL CERTIFICATION NUMBER (`TPR######-###`)** filled in. If those fields are blank, the NOI is still pre-approval and you must wait for DOB to return the stamped version. Do not re-ask Kyle for the TPR number — it's in this PDF.

## Date derivation (no need to ask Kyle)

The three dates on Doc #3 are derived, not stored:

- **Date of Code Deficiency Report** = the **DOB official acceptance date** on the approved NOI (the DATE field inside the FOR OFFICIAL USE ONLY box, alongside STAFF NAME / SIGNATURE / TITLE / NOTICE OF APPROVAL CERTIFICATION NUMBER). NOT the applicant's earlier signature date.
- **Date Corrections Verified** = **today** (the date Kyle asks for the wrap-up).
- **Date of Report Reflecting Approval** = **today** (= signature date at the bottom of Doc #3 = issuing date on Doc #4).

## When asked to prepare a new wrap-up package

1. Locate the approved NOI in the project folder (auto-discoverable, see above) and read its FOR-OFFICIAL-USE-ONLY block to extract the TPR number and the applicant signature date.
2. Locate the discipline `.xlsx` deficiency report(s). Multi-discipline projects (e.g. SPK + FA combined) get **one** wrap-up package with **one** Doc #2 PDF per discipline and a Doc #3 table that has one row per discipline.
3. Produce the 5 output files matching the naming pattern and field conventions above, into the project's own `Wrap up/` subfolder.
4. Ask the user to apply signatures on Doc #3 and Doc #5 before DOB submission.

Ideally the wrap-up metadata (project name, address, disciplines, fixed fields) is captured at proposal-generation time and stored in the project folder, so Doc #3 / #4 / #5 fields are pre-staged when wrap-up is requested.
