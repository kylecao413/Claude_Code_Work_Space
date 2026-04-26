# PE State Applications — Master Folder

Scope: New **comity licensure** in **FL, TX, SC, NC** using NCEES Record 14-528-37.

**DC and MD are already held** — only NCEES Record transmittal is needed to add Fire Protection discipline to those existing licenses. No application forms required for DC/MD.

## Files at this level
- `Master_Info.yaml` — single source of truth. Edit this, re-run `fill_pdfs.py` to regenerate PDFs.
- `fill_pdfs.py` — fills FL / SC / TX PDFs from Master_Info.yaml.

## Per-state folders (4 new states)
| State | Method | Fee | Folder |
|-------|--------|-----|--------|
| FL | Paper PDF + check, mail-only | $230 | `FL/` |
| TX | Hybrid (PDF or online portal) + Ethics exam + fingerprints | $75 + $40 | `TX/` |
| SC | Notarized PDF + online upload | ~$110 | `SC/` |
| NC | Online short form (Option 1 w/ Record) | $0 NC-side | `NC/` |

**Total new-state fees: ~$455** (plus NCEES transmittal to 6 boards: $175 first + $100 × 5 = $675, since DC/MD also need transmittals for the FP add).
**Grand total: ~$1,130.**

## DC / MD (already licensed)
No application needed. Steps:
1. In NCEES account, order Record transmittal to **DC Board of Professional Engineering** ($100 subsequent-state fee).
2. In NCEES account, order Record transmittal to **Maryland State Board for Professional Engineers** ($100).
3. Each board will update your existing PE record with the added Fire Protection discipline once NCEES transmits the FP exam record.

## Recommended sequencing
1. **Today / this week:** confirm NCEES Record is updated with FP exam pass (check NCEES account).
2. **Order NCEES transmittal to all 6 boards simultaneously** (DC, MD, FL, TX, SC, NC).
3. **Mail FL + SC paper applications** (use PREFILLED PDFs in those folders). SC requires notary.
4. **Submit TX via portal or mail**; complete TX Ethics Exam + IdentoGO fingerprints after app accepted.
5. **Submit NC via portal** (Option 1, no fee on NC side).
6. Track status in a spreadsheet.

## Still missing — fill in Master_Info.yaml before final print
Priority items marked `[TBD]`:
- BS graduation year from Dalian University of Technology (resume truncated)
- Exam dates (FE, PE Electrical, PE Civil, PE Fire Protection) — will appear on NCEES Record after FP update posts
- VA PE Civil-Geotechnical license number (same 0402056707 or separate?)
- Reference PE #s and mailing addresses: Ross Garner (American Plan Review), Jeff Tan (Plus Engineering), Ray Bradner (CTI/UES), Fariborz Malek ✓
- VA + MD Master Electrician numbers (only needed if the "other licenses" section is filled)
- Ross Garner's actual email (louis@americanplanreview.com looks like firm inbox — confirm)
