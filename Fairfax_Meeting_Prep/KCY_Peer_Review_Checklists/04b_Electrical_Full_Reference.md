# 04b — Electrical Plan Peer Review (Full Reference)

**Agency:** KCY Engineering Code Consulting LLC
**Code edition:** 2020 NEC (NFPA 70-2020) per VCC reference; 2021 VECC + ASHRAE 90.1 (energy)
**Spine:** 1:1 with Fairfax 2021 Electrical Plan Review Record §A–M.
**Source files:**
- `Plan_Review_Records/2021/Electrical/electrical-plan-review-record-2020.pdf` (form to fill)
- `Common_Rejection_Reasons/Electrical/rej_electrical.pdf`

---

## §A — General Electrical Information

| # | Item | NEC ref |
|---|------|---------|
| A1 | Luminaire schedules including power ratings of each type | Article 410 |
| A2 | Energy compliance method declared on coversheet (ASHRAE 90.1 OR VECC) | VECC |
| A3 | Complete/partial electrical riser diagram | §215.5 |
| A4 | Conductor sizes to panels + equipment | §240.4 |
| A5 | Panel + equipment locations comply with working clearances | §230.72, §110.26 |
| A6 | Load calculations on construction documents | Article 220 |
| A7 | Panel schedules denote loads | §215.5, §220 |
| A8 | Panel schedules contain V, A, # phases, AIC, MCB/MLO | §408.30 |
| A9 | Drawings sealed by VA RDP OR Class A Electrical Contractor / Master Electrical Tradesman | VCC §109.3 |
| A10 | Electrical room doors with listed panic hardware, open in egress direction | §110.26(C)(3) |
| A11 | Available fault current at service equipment | §110.24 |
| A12 | Wiring methods per Article 300 | Article 300 |

## §B — Branch Circuits (Article 210)

| # | Item | NEC ref |
|---|------|---------|
| B1 | GFCI locations | §210.8 |
| B2 | Number of branch circuits | §210.11 |
| B3 | AFCI locations | §210.12 |
| B4 | Dwelling unit receptacle outlets | §210.52 |
| B5 | Lighting outlets | §210.70 |

## §C — Service (Article 230)

| # | Item | NEC ref |
|---|------|---------|
| C1 | Number of services | §230.2 |
| C2 | Service conductor rating (A + V) | §230.23 |
| C3 | Service entrance conductor sizing | §230.23 |
| C4 | Service disconnecting means + CB/fuse sizing | §230.79, §230.90A |
| C5 | Number of disconnecting means | §230.71 |
| C6 | Disconnecting means grouped in one location | §230.72 |
| C7 | GFPE protection for service equipment | §230.95 |

## §D — Feeder (Article 215)

- Feeder conductors sized per §215.2
- Feeder + transformer tap conductors meet tap rules of §240.21 B + C
- Feeder conductors protected by OCPD per §215.3

## §E — Grounding (Article 250)

| # | Item | NEC ref |
|---|------|---------|
| E1 | Main service grounding + supplementary electrodes sized | §250.24, §250.53A(2), §250.66 |
| E2 | GEC / main bonding jumper sized | Tables §250.66 + §250.102(C)(1) |
| E3 | EGC sized | Table §250.122 |
| E4 | Isolated grounding | §250.96B |
| E5 | Intersystem grounding bus bar | §250.94 |
| E6 | Supply-side bonding jumper | §250.102C + Table §250.102(C)(1) |

## §F — Overcurrent Protection (Article 240)

- Conductors + equipment protected by OCPD per §240.4
- OCPD ≤ 800A: next-higher standard rating allowed per §240.4(B)
- OCPD > 800A: conductor ampacity ≥ rating per §240.4(C) + §240.6

## §G — Separately Derived Systems

- Transformers + generators grounded per §250.30
- Transformer OCPD ratings per §450.3
- Primary + secondary OCPD per Tables §450.3(A) + (B)
- Transformer locations per §450.21

## §H — Special Occupancies

| Use group | Article |
|-----------|---------|
| Health care facilities | §517 |
| Commercial garage | §511 |
| Hazardous Class I/II/III | §500 |
| Place of assembly | §518 |
| Medical/dental wiring | §517.12 |

## §I — Special Equipment

| Equipment | Article |
|-----------|---------|
| Signs / outline lighting | §600 |
| Elevators | §620 |
| IT equipment | §645 |
| Pools / fountains | §680 |
| Fire pumps | §695 |

## §J — Emergency Systems (Article 700)

| # | Item | NEC ref |
|---|------|---------|
| J1 | Emergency power source | §700.12 |
| J2 | Exit signs + egress lighting | Article 700-IV |
| J3 | Emergency equipment | §700.12B |
| J4 | Storage batteries ≥ 1.5 hours | §700.12C |
| J5 | Sign at service equipment indicating type + location of emergency power | §700.7 |
| J6 | Only emergency loads on emergency system | §700.15 |
| J7 | Emergency unit equipment fed from same branch as normal lighting, ahead of local switches | §700.12(F) |

## §K — Legally Required Standby (Article 701)

- Adequate capacity + rating for intended loads per §701.4
- Standby power source per §700.12

## §L — Miscellaneous

- Wiring in ducts/plenums/AHU spaces per §300.22
- Motor / appliance / elevator disconnects per §430, §422, §620.51
- EMT + fittings per §358

## §M — Residential

- Residential designs comply with residential provisions of NEC

---

## County rejection-language (from `rej_electrical.pdf`)

| Item | Cite |
|------|------|
| Arc Fault Protection (dwelling family/dining/living/etc.) | §210.12(A) |
| AFCI for replaced receptacles (3 options) | §406.4(D)(4) |
| Basic Power Riser Diagram (panels, service disc, transformers, feeders, OCPDs) | VCC §109.3 |
| OCPD rated ≤ 800A (next-higher standard rule) | §240.4(B) |
| OCPD rated > 800A | §240.4(C) |
| Code Modification Request | VCC §106.3 |
| Branch Circuit Identification (specific purpose, not just "system furniture") | §408.4(A), §90.4 |
| Conductor Overcurrent Protection sizing | §240.4 + §310.15(B), §215.2 |
| Disconnecting means for direct-connected appliance | §422.31 |
| Duct over electrical equipment | §110.26(E) |
| Electrical Energy Compliance box on coversheet | VECC |
| Equipment Grounding Conductor size per Table 250.122 | §250.122 |
| Complete electrical plans (riser, service location, panels, floor plan, schedule, load calc, grounding detail) | VCC §109.3 |
| Emergency lighting unit equipment from normal-lighting branch ahead of switch | §700.12(F) |
| Feeder Conductor Undersized per Table 310.15(B)(16) + §215.2 | §215.2 |
| Provide electrical floor plan | VCC §109.3 |
| GFI-Protected Locations (bathrooms, kitchens, rooftops, outdoor, sinks 6', tubs/showers 6') | §210.8 |
| Intersystem Bonding Terminal | §250.94 |
| Show location of equipment | §110.26 |
| Load Calculations Required | §220 |
| Provide Luminaire Schedule | Article 410 |
| Maximum Available Fault Current | §110.24 |
| Maximum Number of Service Disconnect Switches | §230.71 |
| RDP Seal or Master/Class A Contractor | VCC §109.3 |
| Provide Maintenance Receptacle for HVAC | §210.63 |
| Listed panic hardware on electrical room doors | §110.26(C)(3) |

---

## Companion files
- `04a_Electrical_ScanOrder_Cheatsheet.md`
- `04c_Electrical_PRR_Fillout_Guide.md`
- `00_KCY_Deficiency_Log_Template.docx`
