# SC AHJ TPI/SI Registration Tracker

**Compiled:** 2026-04-27
**Sole-member entity:** KCY Engineer PLLC
**Target individual credential:** Yue Cao, PE/MCP — VA/DC/MD PE held; SC PE comity in flight (`PE_State_Applications/SC/SC_PE_Comity_PREFILLED.pdf`); PE Fire Protection passed 04/16/2026.
**Foreign-qualify entity:** KCY in SC SOS ($125) — required to do business statewide.

---

## Summary Table

| AHJ | Formal program? | Forms downloaded | Email found? | Reg fee | Renewal fee | Status |
|---|---|---|---|---|---|---|
| **SC_LLR_Statewide** | YES — biennial Special Inspector Registration | URLs listed (6 PDFs); manual download required (sandbox blocks curl) | YES — contact.bcc@llr.sc.gov | **$50** | $50 biennial | **READY** (after manual PDF download + Yue's SC PE issues) |
| **Charleston** | YES — formal TPI Program Policy (Sep 2021) | URLs listed (1 program PDF + 1 legacy + 1 IECC); manual download | YES — inspections@charleston-sc.gov | NOT PUBLISHED | NOT PUBLISHED | **NEEDS_OUTREACH** — pre-qualification packet details + insurance + fee |
| **Columbia** | NO formal TPI program — defaults to SC LLR statewide framework | None to download (no city forms exist) | YES — Todd.Beiers@ColumbiaSC.gov + BuildingInspections@ColumbiaSC.gov | $0 city / $50 state | N/A city / $50 biennial state | **NEEDS_OUTREACH** — confirm no city pre-qualification step |
| **Greenville** (City + County) | YES — Greenville **County** has formal Special Inspection Procedure (rev. June 2023). City has no published program. | County procedure PDF URL listed | PARTIAL — general phones only; specific Building Official email NOT yet found | $0 county/city / $50 state | N/A / $50 biennial state | **NEEDS_OUTREACH** — Building Official names + per-category approval workflow |
| **Mount_Pleasant** | NO formal TPI program — per-project prior approval only. TPPR currently CLOSED. | None to download (no formal forms) | YES — inspectionsmp@tompsc.com + buildinginspectionsdivision@tompsc.com | $0 | N/A | **NEEDS_OUTREACH** — discovery meeting required for per-project approval; monitor TPPR reopening |

---

## Critical Findings

### 1. SC LLR Renewal Cycle — Existing TPI_TPPR_Expansion_Research.md is WRONG
- Existing § 2.8 says "Renewal: Annual."
- LLR website confirms: **biennial**, expires June 30 of odd-numbered years. No grace period.
- Current cycle: 2025-2027. Next renewal opens spring 2027.
- **Action:** Update `TPI_TPPR_Expansion_Research.md` § 2.8 — separate task.

### 2. PE/RA Exemption — Local Override
SC §6-8-40 exempts SC-licensed PE/RA from SI registration BUT, per BCC FAQ:
> "...local jurisdictions may impose additional requirements and require the registration anyway. Compliance with local jurisdiction requirements is necessary."
- **Action:** Even after Yue's SC PE comity issues, file the $50 SI registration as belt-and-suspenders.

### 3. Charleston is the ONLY city with a published TPI program
Columbia, Greenville City, Mount Pleasant — none publish formal pre-qualification. Greenville **County** is the exception (county-level procedure document exists). For city-level TPI in those three cities, expect per-project negotiation.

### 4. Sandbox blocked curl downloads — PDFs tracked by URL only
Bash and PowerShell were unavailable in this session due to permission denial. All form URLs are recorded in each AHJ's `forms/URLS.txt` file with target filenames. Manual download via browser is the next step before submitting any application.

---

## Recommended Action Sequence (for KCY post-PE-comity)

1. **Wait for SC PE comity to issue** (`SC_PE_Comity_PREFILLED.pdf` is in flight).
2. **Foreign-qualify KCY Engineer PLLC in SC SOS** ($125).
3. **File SC LLR SI Registration** ($50, biennial) — even though PE-exempt, locals may require.
4. **Apply to Charleston TPI pre-qualification** (manual download of program PDF first).
5. **Submit credentials to Greenville County Building Official** for SI approval.
6. **Outreach calls** to Columbia (Todd Beiers), Greenville City + County Building Officials, Mount Pleasant Building Inspection Division to clarify per-AHJ workflow.
7. **Quarterly re-check** of Mount Pleasant TPPR availability.

---

## Open Questions Carrying Forward to Outreach Phase

Aggregate list across all 5 AHJs (full per-AHJ list inside each README):

- Pre-qualification application fees (Charleston, Mount Pleasant — not published).
- Insurance minimums (all 5 AHJs — none published).
- Building Official names + direct emails (Greenville City, Greenville County, Mount Pleasant).
- Whether SC PE alone sufficient or ICC certs still required per category at each local AHJ.
- Whether KCY Engineer PLLC entity needs separate registration vs only the individual PE.
- Whether SC PE Fire Protection covers Smoke Control SI category.
- TPPR availability windows (Mount Pleasant — currently closed).
