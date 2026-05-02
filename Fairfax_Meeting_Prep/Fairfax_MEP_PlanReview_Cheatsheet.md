# Fairfax County MEP Plan Review Cheat Sheet

**For:** Yue Cao, PE, MCP — Third-Party Plan Reviewer Qualification
**Training:** Day 1 (MEP), 8:00 AM – 12:00 PM
**Adopted code stack (effective 2025-01-18 for all new applications):**

- Virginia Construction Code (VCC) 2021 — `13VAC5-63` Part I (USBC Part I)
- IBC 2021, IMC 2021, IPC 2021, IECC 2021 (as amended by VCC)
- NEC 2020 / NFPA 70-2020 (referenced through VCC Chapter 27)
- IFC 2021 — covered Day 2 (NOT in this sheet)
- Fairfax County Code Chapter 61 (Building Provisions) + Public Facilities Manual (PFM)
- Virginia Code Title 54.1 Ch. 4 (PE/RA seal rules)

> Section numbers in this sheet that start with a bare § are IBC/IMC/IPC/NEC numbers. VCC administrative sections are noted as `VCC §1xx` and live in `13VAC5-63-XX`. When VCC and the model code conflict, **VCC wins**.

---

## 1. VCC 2021 — What It Actually Is

VCC 2021 = **USBC Part I, Construction**, codified at `13VAC5-63` Part I. It is Virginia's legal/administrative wrapper that adopts the 2021 I-codes (IBC, IMC, IPC, IECC, IRC, IFGC, IEBC) and NFPA 70-2020 by reference, then deletes/replaces Chapter 1 of each model code with VCC's own administrative chapter. Translation: when you see "§104 Duties and Powers of the Building Official" in the IBC, **ignore it** — VCC `13VAC5-63-60 (Section 106)` controls instead.

### 1.1 VCC Administrative Sections a Plan Reviewer Must Know

| Topic | VCC § | VAC cite | Notes for plan reviewer |
|-------|-------|----------|-------------------------|
| Enforcement, generally | §104 | 13VAC5-63-40 | Local building department (Fairfax LDS) enforces. As a 3rd-party reviewer you act *under delegation* — final authority remains the Fairfax Building Official. |
| Powers & duties of Building Official | §106 | 13VAC5-63-60 | **§106.3 = modifications / alternative methods / equivalency.** This is the VCC equivalent of IBC §104.10–11. RDP statement may be required (§106.3.1); nationally-recognized performance codes count when approved (§106.3.2). |
| Application for permit | §108 | 13VAC5-63-80 | Defines who can apply, what triggers a permit, exempt activities. |
| Construction documents | §109 | 13VAC5-63-90 | Drawings, specs, energy compliance docs, fire-resistance schedules. **Sealed-by-RDP rule lives here for VA.** |
| Permits | §110 | 13VAC5-63-100 | Issuance, expiration, suspension. |
| Inspections | §113 | 13VAC5-63-130 | Required inspections, third-party inspection allowance. |
| Stop work order | §114 | 13VAC5-63-140 | Issued by Building Official (not the 3rd-party reviewer). |
| Violations | §115 | 13VAC5-63-150 | Class 1 misdemeanor for willful violations. |
| Certificate of occupancy | §116 | 13VAC5-63-160 | No occupancy until CO/TCO issued. |
| Appeals | §119 | 13VAC5-63-190 | Local Building Board of Code Appeals (LBBCA) per Va. Code §36-105; then State TRB. |

> **Common mistake:** Calling out IBC §104.11 for an alternate method. The correct VA citation is **VCC §106.3**.

### 1.2 VA-specific permit-application requirements (vs. base IBC)

- **Sealed drawings** required per VCC §109 *and* Va. Code §54.1-402 — see §6.4 below for exemptions.
- **Energy code compliance documentation** is part of construction docs (COMcheck or equivalent) — VCC §109 incorporates IECC submittal requirement.
- **Designer of record** (RDP) name, VA license number, and seal must appear on cover sheet.
- Owner/applicant signature on permit application.
- For B and M occupancies ≤ certain size, VA allows non-PE/RA design (see §6.4 / Va. Code §54.1-402.A).

---

## 2. Mechanical (IMC 2021) — Top 15 Plan-Review Checks

| # | IMC § | What to check on the drawings | Common deficiency |
|---|-------|-------------------------------|-------------------|
| 1 | §403.3, Table 403.3.1.1 | Outdoor-air ventilation rate calc per occupancy category × people + area component. Must show OA cfm at every AHU. | Designer used "0.06 cfm/sf" rule of thumb without occupancy load; OA cfm not annotated on schedule. |
| 2 | §501–§502 | Exhaust system general — every required exhaust shown, location of termination ≥ 10 ft from openings/property line/OA intake. | Toilet exhaust dumps under soffit < 10 ft from OA louver. |
| 3 | §505 / §507 | Domestic dryer exhaust ≤ 35 ft equivalent, smooth metal, no screws penetrating duct; commercial Type I/II hood ≥ NFPA 96 (also IFC). | Dryer uses flexible foil; no makeup air for hood ≥ 400 cfm (§508). |
| 4 | §506 / §507 | Type I (grease) hood: clearance to combustibles, listed hood, 18-ga grease duct, 18" clearance or listed enclosure, slope, cleanouts. | Grease duct material 22-ga; missing field-applied wrap; no cleanout drawn. |
| 5 | §510 | Hazardous exhaust (lab fume hood, battery rooms): dedicated system, no recirculation, fire damper rules. | Fume hood teed into general exhaust. |
| 6 | §404 | Enclosed parking garage mechanical exhaust ≥ 0.75 cfm/sf or per CO sensor design + makeup air. | No CO sensor strategy; exhaust under-sized. |
| 7 | §701 | Combustion air for fuel-fired appliances — indoor, outdoor, or combo method per Table 703.2. | Boiler room with no CA opening shown; or single 100 sq-in opening for 400 MBH (under-sized). |
| 8 | §801–§804 | Chimney/vent: Cat I draft hood vs Cat IV PVC; clearance to combustibles; termination height (3 ft above roof and 2 ft above any structure within 10 ft, IMC §804.3.4). | PVC vent 4 ft from operable window (req'd ≥ 4 ft horizontal / 1 ft above per §804.3.4). |
| 9 | §1101 (if applicable) | Refrigeration: refrigerant class, machinery-room ventilation, leak detection, max charge per Table 1103.1. | A2L refrigerant in non-classified room; no refrigerant detector. |
| 10 | §306, §304 | Equipment access — 30" × 30" service space, 24" wide passageway, attic/under-floor access dimensions. | Roof RTU within 10 ft of edge with no guardrail; no walkway shown. |
| 11 | §301.6, §304.10 | Water heater / boiler clearances per listing; flue clearance to combustibles. | "Per manufacturer" with no listed values shown — reviewer can't verify. |
| 12 | §603, §604 | Duct material gauge (Table 603.4), insulation R-value per IECC C403.11.3, clearance to combustibles for ducts conveying ≥ 250 °F (§603.7). | Spiral duct exposed in plenum without R-6/R-8 insulation; gypsum board return missing pressure rating. |
| 13 | §607 | **Fire damper / smoke damper / combination damper at every penetration of fire-rated assembly.** Locations on plan must match fire-resistance plan. | Schedule shows FD but plan symbol shows nothing at shaft penetration; access door not called out. |
| 14 | §606 | Smoke detection in supply ducts ≥ 2,000 cfm (and returns ≥ 15,000 cfm in some apps); shutdown of unit on alarm. | No duct smoke detectors shown on RTU sequence. |
| 15 | §306.5 | Roof-top equipment: permanent ladder/stair if > 16 ft to roof; service receptacle within 25 ft of unit (NEC 210.63). | Receptacle missing — coordinate with electrical. |

---

## 3. Plumbing (IPC 2021) — Top 12 Plan-Review Checks

| # | IPC / IBC § | Check | Common deficiency |
|---|-------------|-------|-------------------|
| 1 | IBC §2902 / IPC §403, Table 403.1 | Minimum fixture count by occupancy (M, B, A, E, etc.) and gender split. | Office reno reduced WC count below table without an alternate-method letter. |
| 2 | IPC §404 / ICC A117.1 | Accessible fixtures in each public toilet room — at least one per type accessible. | "Existing to remain" toilet stall doesn't meet 60" turning radius; designer didn't note. |
| 3 | IPC §604 + Appendix E | Water supply sizing — fixture units → demand → main/branch sizing. | One-line plumbing riser with no FU calc; main pipe arbitrarily sized 1". |
| 4 | IPC §607 | Hot water — temperature limit at public lavs 110 °F (mixing valve required). | No ASSE 1070 mixing valve at public lav. |
| 5 | IPC §608 | **Backflow prevention.** RPZ for irrigation/boiler/fire/medical; AVB or PVB for hose bibbs. Cross-connection schedule on drawings. | Missing RPZ on chemical-feed water makeup; no cross-connection table. |
| 6 | IPC §710, Table 710.1(1)/(2) | DWV pipe sizing by drainage fixture units; max DFU per pipe size & slope. | 3" stack carrying 50 DFU (table caps at 48). |
| 7 | IPC §906 + Table 906.1 | Vent sizing & length — ½ × required drain size minimum, max developed length per table. | 1¼" vent serving lavatory exceeds 30 ft developed length. |
| 8 | IPC §504.4, §504.6 | Water heater T&P discharge — full-size to safe location, terminate 6"–24" above floor; **drain pan with 1" indirect drain** if leak would damage. | T&P piped through ½" then back to ¾"; no drain pan in attic. |
| 9 | IPC §305 / §312 | Pipe protection (nail plates, freeze protection); test pressures. | Copper run in exterior wall without insulation in CZ4A. |
| 10 | IFGC 2021 (under IPC volume) §401–§415 | Gas piping: pressure, sizing tables (or CSST manufacturer tables), shutoff at each appliance, sediment trap. | CSST without bonding per NEC 250.104(B); no shutoff at RTU. |
| 11 | IPC §1101–§1108 | Storm drainage — roof drains/overflows sized per rainfall rate (Fig. 1106.1 — Fairfax ≈ 3.1 in/hr, 100-yr 1-hr); secondary drainage required. | No overflow drains/scuppers shown on roof plan. |
| 12 | IPC §312 | Inspection / test arrangement (rough, water test, air test, final). | Specs reference IPC test pressures but plan notes don't. |

---

## 4. Electrical (NEC 2020) — Top 15 Plan-Review Checks

NEC 2020 is referenced through VCC Chapter 27. Citations below are NEC Articles/Sections.

| # | NEC § | Check | Common deficiency |
|---|-------|-------|-------------------|
| 1 | Art. 220, esp. 220.40–220.61 | Service / feeder load calc — connected load, demand factors, largest motor, continuous loads × 125 %. Optional vs. standard method must be declared. | One-line shows 800 A service, calc sheet supports 540 A but uses no demand factors — inconsistent. |
| 2 | 110.26(A) | **Working space at panelboards / switchgear** — depth (Table 110.26(A)(1) — Cond 1/2/3), 30" wide (or width of equipment), 6'-6" headroom. | Panel in janitor closet with mop sink within 36"; no dedicated equipment space (110.26(E)). |
| 3 | 110.26(C) | Egress from working space ≥ 1200 A or ≥ 6 ft wide → two egress paths. | Single door from main switchgear room. |
| 4 | 240.4, 240.6 | OCPD coordination — feeder/branch ratings, standard sizes, tap rules (240.21). | Feeder tap exceeds 25 ft without compliant tap rule. |
| 5 | 210.8 | **GFCI** — all 125 V, 15/20/30 A receptacles in commercial kitchens, bathrooms, rooftops, outdoors, within 6 ft of sinks, garages, etc. | Roof-top receptacle (per IMC §306.5) not called out as GFCI. |
| 6 | 210.12 | AFCI (mostly residential / R-2/R-3 dwelling units). | R-2 unit branch circuits not on AFCI breakers. |
| 7 | Art. 250, esp. 250.24, 250.30, 250.50, 250.66, 250.122 | Grounding electrode system (ground rods, building steel, CEE), grounded-conductor connection, EGC sizing. | Single ground rod without resistance test or supplemental electrode. |
| 8 | 250.104 | Bonding of metal piping (water, CSST, other). | No water-pipe bonding jumper called out. |
| 9 | Ch. 9 Tables 1, 4, 5, 8 + Annex C | Conduit fill (≤ 40 % for ≥ 3 conductors), ampacity adjustment 310.15(C)(1). | 3"+ conductors in same EMT with no derate factor on calc. |
| 10 | 210.52 vs. 210.65 / 314.27(D) | Receptacle spacing — residential per 210.52; commercial uses 210.65 (meeting rooms 12 ft, etc.) and task-specific code. | Conference room shown with one duplex on 30 ft wall. |
| 11 | Art. 700 / 701 / 702 + IBC §2702 | Emergency (life safety), legally required standby, optional standby — separation, transfer means, signage, 10-sec start. | EM and normal in same enclosure without barrier (700.10(D)). |
| 12 | Art. 430, esp. 430.6, 430.22, 430.32, 430.52, 430.110 | Motor circuit — branch-circuit conductor 125 % of FLC, OL at 115/125 %, OCPD per Table 430.52, disconnect within sight or lockable. | Overload missing on motor schedule; OCPD upsize beyond 250 % cap. |
| 13 | Art. 440 | HVAC equipment — disconnect within sight of A/C unit, ampacity per nameplate MCA, OCPD ≤ MOCP. | Rooftop disconnect on opposite side of unit from service access. |
| 14 | Art. 690, 691, 705, 706 (PV/ESS) | Rapid shutdown (690.12), labels (690.13/690.56), 120 % rule (705.12(B)(3)), ESS clearances (706). | Rooftop PV without rapid-shutdown labeling; backfed breaker exceeds 120 % busbar rule. |
| 15 | Art. 517 (if healthcare), Art. 518 (assembly), Art. 600 (signs), Art. 695 (fire pump) | Occupancy-specific articles. | Fire pump tap before service disconnect missing per 695.3 / 695.4. |

> **Lighting controls** live in IECC C405 — see §5 below.

---

## 5. Energy (IECC 2021) — Top 8 Commercial Plan-Review Checks

Fairfax County is in **Climate Zone 4A** (mixed-humid). All envelope/mech/ltg values below assume 4A.

| # | IECC § | Check | Notes |
|---|--------|-------|-------|
| 1 | C402.1.4, Tables C402.1.3 / C402.1.4 | Envelope U-factor or R-value. CZ4A nonresidential examples: roof above-deck R-30ci; mass wall U-0.090; metal-framed wall U-0.064; slab unheated F-0.54. | COMcheck or equivalent compliance form must accompany drawings. |
| 2 | C402.4 | Fenestration U / SHGC — CZ4A NR fixed U ≤ 0.36, SHGC ≤ 0.36 (PF<0.2). Skylight U ≤ 0.50, SHGC ≤ 0.40. | Verify against window schedule; test for area weighting if 30 % WWR exceeded → C402.4.1.1 trade-offs. |
| 3 | **C402.5 (air barrier)** | Continuous air-barrier across thermal envelope — material, assembly, or whole-building test (≤ 0.40 cfm/sf at 0.3 in WC). Detail air-barrier continuity at every transition. | Drawings should call out air-barrier material on wall section + transition details (slab-to-wall, wall-to-roof, fenestration). |
| 4 | C402.5.5 | Vestibules at building entrances (most B, M, R, A). | Often missing on small retail; check against C402.5.5 exceptions. |
| 5 | C403 (mechanical) | Equipment efficiency per Tables C403.3.2(1)–(11) — packaged AC, chiller, boiler, etc. Economizer requirements (C403.5). DCV (C403.7.6). | Schedule must list IEER/EER/SEER2/AFUE/COP — not just tonnage. |
| 6 | C403.11 | Duct/pipe insulation R-values; duct leakage class. | R-6 supply in unconditioned space (was R-3.3 in older sets). |
| 7 | **C405 (lighting)** | Interior LPD by space-by-space or building-area method (C405.3); occupancy/vacancy controls (C405.2.1); daylight controls in primary side- and top-lit zones (C405.2.4); automatic time switch (C405.2.2); receptacle controls (C405.10) — 50 % auto-off in office/computer classroom. Exterior LPD per C405.4. | Lighting schedule must include compliance-method declaration. |
| 8 | C406 | Additional efficiency packages — choose enough credits per Table C406.1. | Often ignored; designer must explicitly list which packages are used. |

> **COMcheck** PDF (envelope + mechanical + lighting) is the de-facto submittal expected by Fairfax. If it's missing, comment it out on first review.

---

## 6. Fairfax-Specific Stuff

### 6.1 Fairfax County Code Chapter 61 (Building Provisions)

Chapter 61 of the Fairfax County Code is the local ordinance that **adopts** the USBC and sets local administrative items (fees, unsafe-building procedures, board of appeals composition). It does **not** add MEP technical amendments — Virginia's Statewide Building Code preempts local technical changes (Va. Code §36-98). Articles include:

- Art. 1 — Administration and Standards (definitions, fees §61-1-3, adoption of USBC)
- Art. 2 — Permits and inspections (administrative supplement only)
- Art. 6 — Unsafe Buildings
- (Other articles — verify exact scope on day-of from Fairfax LDS website if a citation is needed.)

> **Practical takeaway:** Cite VCC and the model codes for technical comments. Cite Chapter 61 only for fees, county-board appeals composition, or unsafe-building procedures. **Do not invent Fairfax MEP amendments** — the technical code is the VCC stack.

### 6.2 Public Facilities Manual (PFM)

PFM is for **site/land-development design** (stormwater, streets, utilities, geotech, landscape) — **not** building MEP. Reviewers see it cited for water/sewer service to the building, fire-flow, on-site stormwater management, pavement section. Hosted at `https://online.encodeplus.com/regs/fairfaxcounty-va-pfm/`.

For an MEP-only plan review, PFM is usually only relevant when:
- Domestic / fire water service sizing references the public main (PFM Ch. 9 — verify on day-of)
- Sanitary sewer connection (PFM Ch. 9)
- Utility easements affect building footprint

### 6.3 LDS / Permit Application Center / ePlans Submission

- **Submission portal:** PLUS Portal — `https://plus.fairfaxcounty.gov/CitizenAccess/Welcome.aspx`
- **Plan review intake:** Building Plan Review, Land Development Services. Phone 703-222-0801.
- Reviewed disciplines: **Building, Mechanical, Electrical, Plumbing, Fire/Life Safety** (Fire Marshal handles IFC).
- Every set must have: signed/sealed cover, drawing index, code analysis (occupancy, construction type, allowable area/height, fire-resistance schedule, MOE summary), specifications, energy compliance docs.
- **Designer of record (DOR):** name, VA license number, seal on cover sheet and on each discipline's first sheet. Each discipline (S, M, P, E, FP) signed/sealed by the engineer of record for that discipline.
- **Expedited / Peer Review Program:** Fairfax also runs a Certified Peer Reviewer program; Yue's qualification falls under this umbrella. The county audits peer reviews and can revoke certification for excessive comments by county staff on peer-reviewed sets — **so be conservative; over-comment beats under-comment.**

### 6.4 VA Registration of Design Professional — When MEP May Be Designed by a Non-PE

**Va. Code §54.1-402.A** lists exemptions from PE/RA license requirement (cite this section, not the IBC, when a designer is unsealed):

- **§54.1-402.A.1** — One/two-family dwellings, townhouses, multifamily up to 3 stories — **excluding** electrical and mechanical systems. *MEP for these still needs a PE.*
- **§54.1-402.A.3** — Use Group **B (Business)** and **M (Mercantile)** buildings, plus churches with occupant load ≤ 100 — **excluding** electrical and mechanical systems. *Architectural can be unsealed; MEP still needs a PE seal.*
- **§54.1-402.A.2** — Farm structures (production/handling/storage of ag products).
- **§54.1-402.B** — Restrictions: **no exemption** for unique structural elements, or for any **Use Group H** (high hazard).

> **Plan-review test:** Look at occupancy + system. If MEP drawings are unsealed and the project isn't a one-/two-family dwelling, the seal exemption probably doesn't apply — comment it. Mechanical and electrical are *explicitly excluded* from the §54.1-402.A.1 and A.3 exemptions.

---

## 7. Submittal Completeness Checklist (One-Page Reject List)

If any of these are missing on first pass, return for resubmittal — don't waste review time on incomplete sets:

| # | Item | Where it lives | Trigger to reject |
|---|------|----------------|-------------------|
| 1 | Drawing index on cover | Cover sheet | Missing or doesn't match actual sheet list |
| 2 | Signed/sealed cover by DOR | Cover sheet | No seal, expired seal, or VA license # missing |
| 3 | Each discipline first sheet sealed by EOR | M-001, P-001, E-001, FP-001 | One discipline unsealed (and not eligible under §54.1-402) |
| 4 | Code analysis / code summary block | Usually G-002 or A-001 | Occupancy, construction type, allowable area/height, sprinklered Y/N, MOE, fire-resistance ratings missing |
| 5 | Fixture count vs. IBC §2902 / IPC §403 | Code summary + plumbing | Calculation table missing or shorts the count |
| 6 | Service / feeder load calc | Electrical narrative or E-001 | One-line not backed by Article 220 calc |
| 7 | Ventilation rate calc per IMC §403 | Mechanical schedule or M-001 | OA cfm not annotated per AHU |
| 8 | Energy compliance — COMcheck (env + mech + ltg) | Sheet G-EN or appended PDF | No COMcheck or stale form |
| 9 | Fire-resistance schedule + UL assemblies | Architectural / G-series | Wall/floor/ceiling ratings without UL # |
| 10 | Penetration / damper details + locations | Mech & Arch | Fire/smoke damper locations not shown at every rated penetration |
| 11 | Equipment schedules (M, P, E, FP) | Each discipline | Missing efficiency, MCA/MOCP, voltage, model, listed values |
| 12 | Specifications | Project manual / annotated specs on plans | No specs at all → reject |
| 13 | Designer of record on cover (Va. §54.1-402 compliance) | Cover sheet | Unsealed and exemption doesn't apply |
| 14 | Owner / applicant signature on permit application | Permit app form | Missing |
| 15 | Means of egress plan (MOE) | A-series | Travel distances, common path, occupant load not shown |

---

## Quick Citation Cheats

- "VCC" = `13VAC5-63` Part I — use VCC §### for *administrative* comments.
- IBC, IMC, IPC, IECC, NFPA 70 — use the *model code* §### for *technical* comments.
- Modifications / alternate methods → **VCC §106.3** (NOT IBC §104.10/11).
- Appeals → **VCC §119** → Fairfax LBBCA → State TRB (Va. Code §36-105).
- Designer-seal exemptions → **Va. Code §54.1-402** (mechanical & electrical *not* exempt for B/M).
- Climate zone for Fairfax County → **CZ 4A** (mixed-humid) — IECC tables.

> **Anything you can't verify in a code book on day-of: write the comment as "Verify per [section] — provide compliance documentation" rather than guessing. Better to ask than to invent a citation.**

---

*End of Day-1 MEP cheat sheet. Day 2 covers IFC 2021 + Fairfax Fire Marshal review — separate document.*
