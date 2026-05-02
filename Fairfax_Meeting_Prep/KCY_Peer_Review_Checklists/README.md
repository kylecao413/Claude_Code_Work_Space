# KCY Peer Review Checklists — Fairfax County

**KCY Engineering Code Consulting LLC** · 2021 VCC · 2026-04-29 build

3 files per trade + cross-cutting addendums + reusable client-deliverable template.

## File map

| # | File | Purpose |
|---|------|---------|
| 00 | `00_KCY_Deficiency_Log_Template.docx` | Reusable client deliverable. Two real columns: Sheet/Detail · Observation+Code. KCY letterhead. **No suggested correction language.** |
| 00 | `_build_deficiency_log_template.py` | Generator script (regenerates the .docx) |
| **01 — Building** | `01a_Building_ScanOrder_Cheatsheet.md` | 1-page sheet-by-sheet scan order — **the fast review tool** |
| | `01b_Building_Full_Reference.md` | Long-form reference for code lookups |
| | `01c_Building_PRR_Fillout_Guide.md` | Line-by-line guide for filling Fairfax 2021 New Commercial / Interior Alterations PRR |
| **02 — Fire Protection** | `02a/b/c_FireProtection_*.md` | Same a/b/c. Includes Smoke Control 3-step pipeline + Fire Marshal Commercial Submittal Requirements integration |
| **03 — Structural** | `03a/b/c_Structural_*.md` | Peer-review-only preface. Uses Building PRR §J + 2021 Special Inspections Program |
| **04 — Electrical** | `04a/b/c_Electrical_*.md` | 2020 NEC. Notes VA Class A Contractor / Master Tradesman seal path |
| **05 — Plumbing** | `05a/b/c_Plumbing_*.md` | 2021 VPC. Plumbing portion of Plumbing/Gas PRR (§A-G + §I) |
| **06 — Mechanical** | `06a/b/c_Mechanical_*.md` | 2021 VMC. Includes commercial kitchen + ventilation + dampers |
| **07 — Gas** | `07a/b/c_Gas_*.md` | 2021 VFGC + NFPA 99 medical gas. Gas portion of Plumbing/Gas PRR (§H) |
| **08 — County Details Addendum** | `08_County_Details_Addendum.md` | Decks / Finished Basements / Carport / Retaining Walls — pre-approved County drawings |
| **09 — Other Agency Coordination** | `09_Other_Agency_Coordination.md` | When to flag Health Dept / Site / Wastewater / Zoning / Fire Marshal commercial reviews to client |

## Workflow

```
                                                 (a) Scan-Order Cheatsheet
                                                          ↓
                          Open plans  →  Tick items  →  Find deficiency  →  Internal Notes (PRR §, code, fix scratch)
                                                                                       ↓
                                                                          Decide: true deficiency?
                                                                                       ↓ Yes
                                                                       Write to Client Deficiency Log .docx
                                                                       (Sheet / Observation + Code only)
                                                                                       ↓
                                                                       Fill Fairfax PRR form
                                                                       (using c_PRR_Fillout_Guide.md per trade)
                                                                                       ↓
                                                                       Sign + submit with construction docs
```

## Two-tier output rule (non-negotiable)

**Internal notes** (KCY only): PRR §, suggested-fix scratch, County rejection-language refs.
**Client log**: observation + code citation. **NO suggested correction language.** Conflict of interest.

## Source PDFs (parent folder `Fairfax_Meeting_Prep/`)

- `Plan_Review_Records/2021/{trade}/` — the PRR forms KCY fills as deliverable
- `Plan_Review_Records/2018/{trade}/` — kept on file for legacy projects only
- `Common_Rejection_Reasons/{trade}/` — County's "common mistake" list (rejection-language source)
- `Submission_Resources/{Building, Smoke_Control, Structural}/` — coversheet, smoke control manual + supplemental, Special Inspections Program
- `Other_Agency_Reviews/Fire_Marshal_Commercial/` — FM commercial submittal requirements
- `County_Details/{Decks, Finished_Basements, Carport_Enclosures, Retaining_Walls}/` — pre-approved arch plans

## Time budgets per review

| Trade | Tenant interior | New commercial |
|-------|-----------------|----------------|
| Building | 45 min | 90 min |
| Fire Protection | 50 min | 90 min |
| Structural | 30 min (rare) | 75 min |
| Electrical | 30 min | 60 min |
| Plumbing | 30 min | 50 min |
| Mechanical | 40 min | 75 min |
| Gas | 15 min | 30 min (60 if med gas) |

## Status

Draft 1 — pending Kyle markup. After first real Fairfax peer review, refine cheatsheets + deficiency log columns based on what was actually used.
