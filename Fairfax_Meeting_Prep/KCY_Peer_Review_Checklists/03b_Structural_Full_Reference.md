# 03b — Structural Plan Peer Review (Full Reference)

**Agency:** KCY Engineering Code Consulting LLC
**Code edition:** 2021 VCC Ch 16 (Structural Design) + Ch 17 (Special Inspections), 2018 IBC referenced, ASCE 7-16, ACI 318 / AISC 360 / NDS / TMS 402 as applicable, ANSI MH 16.1 (storage racks).
**Spine:** Structural items live within the **Building PRR §J** (New Commercial form) plus **Statement of Special Inspections** form (`sip_ssi.pdf`). There is no separate Structural Plan Review Record.
**Scope:** Peer review only. Fairfax retains official structural review + shop drawing review.
**Source files:**
- `Plan_Review_Records/2021/New_Commercial_Building/new-commercial-building-plan-review-record-2021.pdf` (§J only)
- `Submission_Resources/Structural/2021-special-inspections-program.pdf`
- `Submission_Resources/Structural/sip-final-report.doc`, `sip-stripping-letter.doc`, `sip-temperature-log.doc`
- `Common_Rejection_Reasons/Building/rej_building_commercial.pdf` (structural items)

---

## §1 — Design loads on plans (VCC §1603)

All loads must be on plans, with Fairfax-specific values:

| Load | Value | Code |
|------|-------|------|
| Snow Pg (ground) | **25 psf** | §1603.1.3 |
| Wind V (basic) | **90 mph (40 m/s)** | §1603.1.4 |
| Wind Vult (ultimate) | **115 mph (51 m/s)** | §1603.1.4 |
| Seismic Ss | **0.129** | §1603.1.5 |
| Seismic S1 | **0.053** | §1603.1.5 |

For each load type, the plans must list:

| §1603.1.3 Snow | §1603.1.4 Wind/Tornado | §1603.1.5 Seismic | §1607 Live |
|----------------|------------------------|--------------------|------------|
| Pg, Pf, Ce, I, Ct | V, Vt, Vasd, Risk Cat, Exposure, GCpi, C&C pressure | Risk Cat, IE, mapped + design SRP, Site Class, SDC, SFRS, base shear, Cs, R, analysis procedure | Per Table 1607.1 by occupancy |
| Drift Pd, W if applicable | | | Concentrated loads |

Live load for means of egress ramp = 100 psf (§1607.1).

---

## §2 — Foundation (VCC §1806, §1809, §1810)

### §2.1 Geotechnical report
- Required when soil bearing > 2,000 psf assumed OR any deep foundation method
- Sealed by VA-licensed RDP (architect or engineer)
- Maximum assumable soil bearing capacity without geotech investigation = 2,000 psf

### §2.2 Shallow foundations (§1809)
- Foundation plan with footing schedule
- Min frost depth 24" (Fairfax)
- Bearing pressure on plans matches geotech assumption

### §2.3 Deep foundations (§1810)
**Triggers special inspection.** Includes: aggregate piers, driven piles (steel/concrete/timber), caissons, auger-cast piles, helical piers, micropiles.

Required documentation:
- Complete deep foundation design (Fairfax County policy)
- Geotechnical report covering installation area (§1810.1, §1803)
- Lateral/stability/settlement/group-effect analysis (§1810.2)
- Plan note: mfg, model, size, length, shaft diameter, bearing plate count/size/thickness, plus any other critical info uniquely identifying the pile (§1810.3.1.5, §1810.3.5.3.3)
- Allowable axial design load per method of §1810.3.3.1.9
- Subject to special inspection — listed on SSI

### §2.4 Aggregate Pier (Intermediate Foundation / Soil Reinforcement)
Supplemental foundation system to shallow foundations of §1809. Required:
- ICC-ES Evaluation Report
- Engineering design with system details (size, depth, location)
- Soil report
- Listed on SSI (§1809)

---

## §3 — Structural design + details (VCC §109.3, §1603.1)

| Item | Code |
|------|------|
| Foundation Plan with column + footing schedule | §109.3 |
| Framing Plan(s) showing all structural members + sizes + sections + locations dimensioned, column centers + offsets dimensioned | §1603.1 |
| Connection / attachment details | §109.3 |
| Wall sections | §109.3 |
| Lateral-system details | §1604.5, §1605 |
| Diaphragm details | — |

---

## §4 — Trusses + pre-fab + special (VCC §109.3, ICC §2209)

| Item | Code |
|------|------|
| Floor / Roof Truss drawings — Truss Plan Cover Sheet (`trusscvr.pdf`) + truss drawings | §109.3 |
| Truss drawings sealed by truss design engineer; submit before installation | §109.3 |
| Pre-fab buildings — calcs + structural details for entire framing | §109.3 |
| Storage racks > 12' height — calcs + framing + anchorage; subject to special inspection | ICC §2209, RMI/ANSI MH 16.1 |
| HVAC equipment attachment detail — angles, channels, rods, bolts, welds + adequacy calc | §109.3 |

---

## §5 — Industrialized buildings (13 VAC 5-91)

- Foundations for industrialized building + accessible-entrance stair/ramp; min frost depth 24"
- Tie-downs per mfg recommendations (proper anchorage)
- Manufacturer's installation instructions with plans
- 60% public entrances accessible (§1105.1)
- Ramp design live load 100 psf (§1607.1); guards if rise > 30" AFG (§1015); handrails per §1014

---

## §6 — Special Inspections Program (VCC §109.4, Ch 17)

### §6.1 Statement of Special Inspections form (`sip_ssi.pdf`)
- Complete page 1 (project info)
- Pages 2-3: every item marked Yes or No — no blanks
- Sealed + signed + dated by **Structural Engineer**

### §6.2 Special Inspections Meeting
Required prior to permit issuance. Note on plans.

### §6.3 SI categories (typical scope on the form)
- Soils (excavation, fill, subgrade, foundation)
- Concrete (rebar, mix, placement, cylinders)
- Masonry
- Steel (welds, bolts, fabrication, erection)
- Cold-formed steel
- Wood (LVLs, glulams, prefabricated)
- EIFS (per ICC-ES eval report; §1408)
- Post-installed anchors (per ICC-ES eval report; §1908.2)
- Anchorage to concrete (post-installed)
- Sprayed fire-resistant materials
- Smoke control systems (cross-reference Smoke Control Supplemental Checklist)
- Helical piles, aggregate piers (deep foundation)
- Storage racks > 12'
- Fire-rated assemblies
- Structural Observation per §1704.6.1 (if triggered) — SE submits written statement to BO identifying frequency + extent

### §6.4 Final Report of Special Inspections
- Form: `sip-final-report.doc`
- Sealed by SE
- Required prior to CO

### §6.5 Cold weather concrete (winter pours)
- Form: `sip-temperature-log.doc`
- Required when ambient < 40°F

### §6.6 Stripping/shoring authorization
- Form: `sip-stripping-letter.doc`
- Required prior to formwork removal/stressing

---

## §7 — Proprietary / ICC-ES products (VCC §112.2)

Required for: anchors, adhesives, fasteners, EIFS, proprietary devices.
- Copy of acceptance evaluation report
- Identify report number in drawings
- Out-of-date reports → reject + request current

---

## §8 — Foundation & Footing permit (early submittal)

For Foundation & Footing permits (before full building permit):
- Calcs + structural + architectural details of entire building
- Reference: `https://www.fairfaxcounty.gov/landdevelopment/foundation-and-footing-permits`

---

## §9 — Sheeting and shoring

Separate permit + plan submission required. Soils report + sealed calcs may be required (§108.1, §109.1).

---

## §10 — Retaining walls

Separate permit (per §108.1, §109.1). Soils report + sealed calcs may be required. See `County_Details/Retaining_Walls/retaining-wall-details.pdf` for County's pre-approved details (when applicable, residential or small commercial).

---

## County rejection-language (structural items from `rej_building.pdf`)

| Frequency | County's title | Cite |
|-----------|----------------|------|
| Very high | Live Loads required on plans | §1607.1 |
| Very high | Structural loads + factors required | §1603.0 |
| Very high | Wind load + factors required (Fairfax-specific values) | §1603.1.4 |
| Very high | Seismic load + factors required | §1603.1.5 |
| Very high | Snow load + factors required (Pg = 25 psf) | §1603.1.3 |
| Very high | Soils report required | §1803 |
| Very high | SSI form missing / incorrect / incomplete | Ch 17 |
| High | Special Inspections meeting required | Ch 17 |
| Mid | Helical piles design data | §1810 |
| Mid | Aggregate piers design data | §1809 |
| Mid | Structural calcs required (sealed, VA RDP) | §109.3 |
| Mid | Footing & Foundation calcs (full building) | §109.3 |
| Mid | Pre-fab building calcs | §109.3 |
| Mid | Storage rack calcs (>12') | §2209 |
| Mid | HVAC attachment detail | §109.3 |
| Mid | EIFS evaluation report required | §1408 |
| Mid | EIFS evaluation report installation details | §1408 |
| Mid | Out-of-date evaluation report | §112.2 |
| Mid | Industrialized Building Affidavit | 13 VAC 5-91 |
| Mid | Submit roof/floor truss drawings (Truss Plan Cover Sheet) | — |

---

## Companion files

- `03a_Structural_ScanOrder_Cheatsheet.md` — fast review tool
- `03c_Structural_PRR_Fillout_Guide.md` — fill-out guide for Building PRR §J + SSI form
- `00_KCY_Deficiency_Log_Template.docx` — client deliverable
