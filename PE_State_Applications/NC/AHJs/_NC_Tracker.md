# North Carolina AHJ Tracker — KCY Engineer PLLC

**Prepared:** 2026-04-27
**State:** North Carolina
**Entity:** KCY Engineer PLLC (foreign-qualifying in NC)
**PE-of-Record:** Yue Cao, PE/MCP — VA + DC + MD active; **NC PE comity in flight via NCEES (online portal); PE Fire Protection passed 2026-04-16**
**Statute:** NCGS Ch. 160D Article 11 (owner-elected TPI/TPPR) + NCBC Ch. 17 (Special Inspections)
**State-level research:** `TPI_TPPR_Expansion_Research.md` § 2.3
**State PE prefilled answers:** `PE_State_Applications/NC/NC_Portal_Answers.md`

---

## Tracker Matrix

| AHJ | Formal program? | Forms downloaded? | Email found? | Reg fee | Renewal fee | Status |
|---|---|---|---|---|---|---|
| **Mecklenburg County (Charlotte)** | Yes — formal `meck-si.com` / Accela SIF + DSI/ASI registration | URLs captured (10 PDFs); bash disabled — manual DL needed | Meck-SI@mecklenburgcountync.gov | Legacy $99 / new ~$225 (Accela) — confirm via Q2 | Annual ~$225 (per Dec 2025 letter) | **NEEDS_OUTREACH** — confirm Accela fee schedule, insurance limits, in-state office requirement |
| **Wake County / Raleigh** | No standing list; per-project Third Party Inspections Agreement | URLs captured (Agreement + Schedule); bash disabled — manual DL | james.thompson@raleighnc.gov; bryan.robinson@raleighnc.gov; Wake.Permitting@wake.gov | $0 | None — per-project | **NEEDS_OUTREACH** — confirm COI minimum, TPPR availability, Wake County form parity |
| **Greensboro** | Document-based: Statement + Field Tech Quals + Final Cover Sheet | URLs of pages captured; **WebFetch returned 403** on permits page — Kyle must browse manually | Department phone 336-373-2302; APRIL 336-373-2400; Director Kenney McDowell (firstname.lastname@greensboro-nc.gov) | $0 | None | **NEEDS_OUTREACH** — get the three SI forms via browser, confirm SI coordinator email + COI minimum |
| **Durham (City-County Building & Safety)** | **No published program** — pure NCBC Ch. 17 default | No Durham-specific TPI form found; default to NC SCO Statement template | wyatt.blalock@durhamnc.gov (Chief Building Inspector); jim.rodgers@durhamnc.gov (Field Supv); 919-560-4144 main | $0 | None | **NEEDS_OUTREACH** — call/email Wyatt Blalock to confirm TPI workflow exists at all |
| **Buncombe County (Asheville unincorporated)** | Document-based: Special Inspection & Testing Agreement + RDP Inspection Form (strict — only form accepted) | URLs captured (3 PDFs); bash disabled — manual DL needed | jason.rogers@buncombecounty.org (Director); permitdocs@buncombecounty.org (submissions); Eric Evans 828-776-1089 (Plan Review) | $0 | None | **READY** — forms are clear, contacts verified, no annual reg; just need NC PE issuance + per-project filing |

---

## Summary by Status

### READY (1)
- **Buncombe County** — All three forms identified, strict published rule ("no other form accepted"), Director email verified. KCY can begin pitching as soon as Yue's NC PE issues. No firm-level registration step.

### NEEDS_OUTREACH (4)
- **Mecklenburg County** — Highest priority. Formal program but mid-migration to Accela; current 2026 fee schedule + COI minimums + in-state office rule must be confirmed by phone/email before applying.
- **Wake County / Raleigh** — Per-project agreement, but COI/insurance limits unpublished and Wake County (unincorporated) parity uncertain.
- **Greensboro** — Forms exist but WebFetch couldn't pull them past 403; Kyle must fetch via browser. Also need SI coordinator's name/email.
- **Durham** — No published TPI workflow at all. Must call Chief Building Inspector to confirm whether the AHJ formally accepts third-party SI under NCGS 160D / NCBC Ch. 17.

---

## Universal Open Questions (all 5 AHJs)

1. **Insurance:** What is each AHJ's required Professional Liability / GL / WC minimum? (industry default $1M Pro)
2. **TPPR availability:** Does the AHJ accept third-party PLAN REVIEW under NCGS 160D-1110, or only SI inspections?
3. **Field-tech residency:** Can KCY use VA/DC-based ICC-certified inspectors under the NC PE's responsible charge, or must inspectors be NC-resident?
4. **In-state office:** Is foreign-qualified PLLC with VA/DC office acceptable, or does any AHJ require a NC physical office?
5. **RDPIRC structure:** Must the responsible NC PE be a W-2 employee, or is 1099 contracting acceptable?

---

## Pre-Action Checklist (before any AHJ outreach)

- [ ] Yue's NC PE comity application submitted via NCEES (see `NC_Portal_Answers.md`)
- [ ] KCY Engineer PLLC foreign qualification with NC SOS submitted
- [ ] COI obtained: $1M Pro Liability + $1M GL + statutory WC (raise Mecklenburg's specific limits if higher)
- [ ] Capability statement / 1-page firm profile drafted for NC AHJ outreach (do NOT draft yet — per instructions)
- [ ] All 5 AHJ form PDFs manually downloaded into respective `forms/` subfolders (bash was disabled this session)
- [ ] Mecklenburg Accela account created at https://aca-prod.accela.com/Mecklenburg/Home.html

---

## Files Created This Session (2026-04-27)

```
PE_State_Applications/NC/AHJs/
├── _NC_Tracker.md  (this file)
├── Mecklenburg_County/
│   ├── README.md
│   ├── forms/         (empty — URLs in README; bash disabled, manual DL needed)
│   └── templates/
├── Wake_County_Raleigh/
│   ├── README.md
│   ├── forms/         (empty)
│   └── templates/
├── Greensboro/
│   ├── README.md
│   ├── forms/         (empty — 403 on WebFetch, manual browser DL needed)
│   └── templates/
├── Durham/
│   ├── README.md
│   ├── forms/         (empty — no Durham-specific TPI form exists publicly)
│   └── templates/
└── Buncombe_Asheville/
    ├── README.md
    ├── forms/         (empty — URLs in README; bash disabled)
    └── templates/
```

> **Note on form downloads:** Bash and PowerShell were denied during this research session, so the `forms/` subfolders were created via Write tool placeholders (this README in each AHJ folder). All form URLs are recorded in each AHJ's README.md. Kyle should re-run with bash enabled, or download the PDFs manually via browser.
