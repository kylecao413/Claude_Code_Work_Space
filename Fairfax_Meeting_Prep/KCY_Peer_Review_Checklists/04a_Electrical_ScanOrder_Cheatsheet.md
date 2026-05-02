# 04a — Electrical Plan Peer Review Scan-Order Cheatsheet

**KCY Engineering Code Consulting LLC** · 2020 NEC (per VCC) · Fairfax County

---

## Round 1 — 5-min binary check

- [ ] Coversheet **Electrical Energy Compliance** box checked (ASHRAE 90.1 OR VECC) — if missing, automatic rejection
- [ ] Drawings sealed by **VA RDP** OR **Class A Electrical Contractor / Master Electrician** (NEC accepts either per VCC §109.3)
- [ ] Power riser diagram on plans
- [ ] Panel schedules with: V, A, # phases, AIC, MCB/MLO (NEC §408.30)
- [ ] Load calculations on construction documents (NEC §220)

---

## Round 2 — Sheet-by-sheet

### E0.0 — General Notes / Riser (5 min)
- [ ] Code: 2020 NEC + VCC amendments + 2018 VECC / ASHRAE 90.1 + ICC A117.1-2009
- [ ] Available service fault current noted (NEC §110.24)
- [ ] Power riser diagram with: service entrance, transformers, distribution panels, panel boards (new + existing, including those feeding the new ones), feeder sizes + conduits, OCPDs ratings + locations
- [ ] Service or transformer grounding detail with electrode conductor sizes + electrodes used
- [ ] Service equipment doors equipped with **listed panic hardware** opening in egress direction (NEC §110.26(C)(3))
- [ ] Wiring methods per NEC Article 300

### E1.x — Lighting / Receptacle Plans (4 min)
- [ ] Luminaire schedule including power ratings per type (NEC Article 410)
- [ ] Lighting outlets per §210.70
- [ ] **GFCI** locations per §210.8 (bathrooms, kitchens, rooftops, outdoors, sinks within 6', bathtubs/showers within 6', etc.)
- [ ] **AFCI** locations per §210.12 (dwelling unit family/dining/living/bedroom/parlor/library/den/sunroom/rec/closets/hallways)
- [ ] AFCI for replaced receptacles per §406.4(D)(4) (3 options)
- [ ] Dwelling unit receptacles per §210.52
- [ ] Branch circuits identified — clear, evident, specific purpose; large open office workstations uniquely identified (not just "system furniture")
- [ ] Number of branch circuits per §210.11
- [ ] Maintenance receptacle for HVAC

### E2.x — Power Plans (4 min)
- [ ] Service: number per §230.2; conductor rating + voltage per §230.23; entrance conductor sizing per §230.23
- [ ] Service disconnecting means + CB/fuse properly sized (§230.79, §230.90A); number per §230.71; grouped per §230.72
- [ ] GFPE for service equipment per §230.95
- [ ] Feeder conductors sized per §215.2; tap rules per §240.21 B + C; OCPD per §215.3
- [ ] Conductor sizes to panels + equipment per §240.4
- [ ] Panel + equipment locations per §230.72 + §110.26 (working clearances)
- [ ] **Mechanical duct NOT located above electrical panelboard** (§110.26(E))

### Grounding (NEC Article 250) (3 min)
- [ ] Main service grounding + supplementary electrodes per §250.24, §250.53A(2), §250.66
- [ ] GEC + main bonding jumper per Tables §250.66 + §250.102(C)(1)
- [ ] EGC sized per Table §250.122 (cannot be smaller than table; never larger than circuit conductors)
- [ ] Isolated grounding per §250.96B
- [ ] Intersystem grounding bus bar per §250.94
- [ ] Supply-side bonding jumper per §250.102C + Table §250.102(C)(1)

### OCPD (NEC Article 240) (1 min)
- [ ] Conductors + equipment protected per §240.4
- [ ] OCPD rated ≤ 800A: next-higher standard rating allowed if (a) not single-receptacle branch for cord-and-plug portables, (b) ampacity doesn't correspond to standard rating, (c) next higher ≤ 800A — §240.4(B)
- [ ] OCPD > 800A: conductor ampacity ≥ device rating per §240.4(C) + §240.6

### Separately Derived Systems (§250.30, §450) (2 min)
- [ ] Transformer + generator grounded per §250.30
- [ ] Transformer OCPD primary + secondary per Tables §450.3(A) + (B)
- [ ] Transformer location per §450.21

### Special Occupancies (1 min — N/A unless triggered)
- [ ] Health care: §517 (medical/dental wiring per §517.12)
- [ ] Commercial garage: §511
- [ ] Hazardous Class I/II/III: §500
- [ ] Place of assembly: §518

### Special Equipment (2 min)
- [ ] Signs/outline lighting: §600
- [ ] Elevators: §620 (disconnecting means per §620.51)
- [ ] IT equipment: §645
- [ ] Pools/fountains: §680
- [ ] Fire pumps: §695

### Emergency + Standby Systems (3 min)
- [ ] Emergency power per §700.12
- [ ] Exit signs + egress lighting per §700-IV
- [ ] Emergency equipment per §700.12B
- [ ] Storage batteries supply ≥ 1.5 hours per §700.12C
- [ ] Sign at service equipment indicating type + location of emergency power per §700.7
- [ ] Only emergency loads on emergency system per §700.15
- [ ] Emergency lighting unit equipment fed from same branch as normal lighting, ahead of local switches per §700.12(F)
- [ ] Legally required standby per §701.4 + §700.12

### Misc (1 min)
- [ ] Wiring in ducts/plenums/AHU spaces per §300.22
- [ ] Motor / appliance / elevator disconnects per §430, §422, §620.51
- [ ] EMT + fittings per §358

### Residential (1 min — N/A unless residential)
- [ ] Residential designs per residential provisions of NEC

### Energy Compliance
- [ ] Coversheet box checked — ASHRAE 90.1 OR VECC
- [ ] If VECC: Electrical Energy Certification Form OR coversheet box

---

## Round 3 — Output

For every FAIL → internal note → if true deficiency → client log row (Discipline = "Electrical").

**Time budget:** ~30 min tenant interior / ~60 min new commercial.
