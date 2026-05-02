# Fairfax County Fire Protection Plan Review — Cheat Sheet

**Reviewer:** Yue Cao, PE (Fire Protection PE, passed 2026-04-16), MCP
**Training session:** 2026-04-29, 08:00–10:00
**Purpose:** Qualification as a Fairfax County third-party plan reviewer (FP discipline)
**Code stack on the desk:** IFC 2021 (via VSFPC), IBC 2021 Ch. 7 + 9, NFPA 13/14/17/17A/20/24/25/70/72/80/92/96/2001, NFPA 101 (reference only), Fairfax FMO amendments + PFM Ch. 9.

> Verify with FMO before issuing any first-pass review: Fairfax has been transitioning between the 2018 and 2021 USBC/SFPC packages. As of the public website snapshot, the active Code Reference Package (CRP) is the 2018 CRP v2 (Feb 2024); 2021 USBC projects are starting to flow through. Confirm at intake which code package applies to each permit. Phone: **703-246-4806** / **fire.engplansreview@fairfaxcounty.gov**.

---

## 1. VSFPC vs IFC — the legal frame

- **VSFPC (Virginia Statewide Fire Prevention Code) = Virginia's adoption of IFC 2021**, with state amendments. Adopted jointly by the Board of Housing and Community Development (BHCD) and the Virginia Fire Services Board.
- **VSFPC is a maintenance/operations code**. Virginia state law strips out construction-related provisions from IFC and locates them in the **VCC (Virginia Construction Code, part of the USBC)**. In practice: most amendments are editorial deletions of construction language. Anything *built* is governed by VCC; anything *operated/maintained* after CO is governed by VSFPC.
- **Construction-phase fire protection plan review** therefore lives mostly under the **VCC (USBC Part I) → IBC 2021 + IFC 2021 referenced standards**, with VSFPC kicking in at and after the CO.
- **Enforcement split in Fairfax:**
  - **Building Official (Land Development Services / Building Plan Review):** VCC (USBC), IBC, structural, occupancy classification, means of egress documentation on the architectural set.
  - **Fire Marshal Office (FMO) Engineering Plans Review Branch:** Fire alarm, sprinkler, standpipe, fire pump, private fire service main, smoke control, kitchen suppression, tank, special locking, ERCES, fire-lane / apparatus access, Knox box. Reviews per VSFPC + USBC + Fairfax local amendments + PFM Ch. 9 + NFPA standards referenced by USBC Chapter 35.
- **FMO can adopt MORE-restrictive local amendments** under county code authority. Always check the current Fairfax County Fire Prevention Code amendments and the active CRP version before applying base IFC verbatim.

---

## 2. Sprinkler plan review (NFPA 13 + IBC §903) — top 12 checks

1. **Where required** — IBC §903.2 by occupancy. Memorize the trigger thresholds: A-1/A-2 over 100 occ or 5,000 sf fire area; A-3/A-4 over 12,000 sf; B/F-1/M/S-1 over 12,000 sf or 3 stories; R-1/R-2/R-4 throughout; E over 12,000 sf; H — throughout per hazard. **High-rise (§403)**: sprinklers + secondary water supply throughout.
2. **Hazard classification (NFPA 13 §4.3 / Ch. 4 of 2019 ed.):** LH (light hazard — offices, schools, residences), OH-1 (parking, restaurants seating), OH-2 (mercantile, light manufacturing, repair garages), EH-1 (woodworking, die casting), EH-2 (flammable liquids, plastics, rubber). **Wrong hazard classification is the single most common reviewer rejection** — verify against the actual use, not just the occupancy letter.
3. **Density/area curve (NFPA 13 §19.2 / Fig. 19.2.3.1.1):** LH 0.10 gpm/sf over 1,500 sf; OH-1 0.15/1,500; OH-2 0.20/1,500; EH-1 0.30/2,500; EH-2 0.40/2,500. Apply the **density/area method** OR room-design method. Confirm the design point is on the curve, not below it.
4. **Hose stream allowance (NFPA 13 Table 19.2.3.1.2):** LH 100 gpm / 30 min; OH 250 gpm / 60–90 min; EH 500 gpm / 90–120 min. Hose allowance is added at the **base of riser / connection to supply**, not at the sprinkler.
5. **Hydraulic calculation review:** Starting point = most hydraulically remote area. Verify (a) C-factor (120 for new black/galv steel, 150 for copper/CPVC), (b) pressure loss totals, (c) elevation losses, (d) **safety margin: 10 psi or 10% above demand at the supply point, whichever is greater** (NFPA 13 §28.2.4.2). Reviewers reject if margin is razor-thin or absent.
6. **K-factor + spacing:** K-5.6 standard, K-8.0 / K-11.2 / K-14.0 / K-16.8 / K-22.4 / K-25.2 for higher-density and storage. Spacing per NFPA 13 §10–13: max coverage area LH 225 sf (200 sf for combustible), OH 130 sf, EH 100 sf. Max spacing 15 ft LH, 15 ft OH, 12 ft EH. Min spacing 6 ft (4 ft with baffle).
7. **Obstruction rules — NFPA 13 §10.2.7:** the "**4-times rule**" (sprinkler must be ≥4× the obstruction max-dimension away from a continuous obstruction) and the **beam rule** (Table 10.2.7.2 or 11.2.7.2 — distance from sprinkler to side of beam vs. deflector-above-beam-bottom). Catch dropped soffits, ductwork, light fixtures, and beams cutting through coverage zones.
8. **ESFR vs CMSA:** ESFR (early suppression fast response, K-14/17/22/25, NFPA 13 Ch. 23) — used in storage/warehouses, no in-rack typically required. CMSA (control mode specific application, K-11.2/16.8/19.6/25.2, Ch. 22) — control rather than suppress. Verify ceiling slope ≤2/12 for ESFR, obstruction rules tighter, minimum operating pressure on the curve.
9. **Underground supply / lead-in / FDC:** NFPA 24. Verify (a) hydrant flow test data ≤12 months old, (b) FDC location 15–100 ft from hydrant, on street side, with 7.5 ft clear, (c) **Fairfax: FDC threads = 5" Storz** (verify with FMO) — Fairfax/NoVA standardized on Storz years ago, (d) post-indicator valve (PIV) on lead-in if required.
10. **Backflow preventer:** Per Fairfax/Virginia DPOR cross-connection rules — typically **DCDA (double check detector assembly)** for sprinkler-only on potable supply; **RPZ (reduced pressure zone)** if antifreeze, foam, or chemical additives are present, or for high-hazard occupancies. Confirm with Fairfax Water cross-connection control program.
11. **Antifreeze (NFPA 13 §7.6, 2019 ed.):** Major restriction since 2013 cycle — only **listed antifreeze solutions** allowed in new systems. Glycerin/propylene glycol mixed on-site is no longer permitted for new installs in occupied dwelling units. Existing systems: phase-out path. Reject any new system specifying field-mixed antifreeze.
12. **Pipe schedule vs hydraulically designed + 13R/13D:** NFPA 13 §28.5 pipe-schedule allowed only for additions to existing pipe-schedule systems and only for LH/OH-1 within size limits. Otherwise **hydraulically calculated**. **NFPA 13R**: R-1/R-2/R-4 up to 4 stories above grade plane and ≤60 ft to highest occupied floor. **NFPA 13D**: 1- and 2-family dwellings and townhomes. Confirm story count and height correctly drives the standard chosen.

---

## 3. Standpipe (NFPA 14 + IBC §905) — top 8 checks

1. **Class I** (2½" for FD use), **Class II** (1½" for occupant use — rarely required new), **Class III** (both — schools, large assemblies). IBC §905.3 sets the trigger.
2. **Where required (§905.3):** building height >30 ft above/below lowest level of FD access; covered/open mall buildings; A occupancy >1,000 occ; underground >30 ft below; helistops/heliports; stages >1,000 sf.
3. **Hose connection locations (§905.4):** every floor at every required exit stairway intermediate landing (or main landing where intermediate not feasible); on each side of horizontal exits; in each exit passageway; **on the roof** if roof slope <4:12 and any equipment requires servicing; in covered/open malls at entrances to each tenant.
4. **Pressure (NFPA 14 §7.8 / IBC §905.4.1):** **min 100 psi residual at the topmost outlet of the most remote standpipe** at 500 gpm flow (250 gpm for additional standpipes, max 1,000 gpm Class I/III; 100 gpm for Class II). **Max 175 psi** static at any outlet — pressure-regulating devices required above that.
5. **Flow demand (NFPA 14 §7.10):** 500 gpm first standpipe + 250 gpm each additional (Class I/III), capped at 1,000 gpm (sprinklered) / 1,250 gpm (non-sprinklered).
6. **Zoning for high-rise:** **Vertical zone limit ≈275 ft** (max design pressure constraint). High-rise = building with occupied floor >75 ft above lowest FD-vehicle access (IBC §202). Zones are split with intermediate fire pumps + express risers.
7. **Fire pump interlock:** verify pump start signal from standpipe pressure switch, jockey pump cuts in/out points, sequence diagram on plans.
8. **FDC for standpipe:** NFPA 14 §7.12 — separate FDC or combined sprinkler/standpipe FDC; ID signage required.

---

## 4. Fire pump (NFPA 20) — top 8 checks

1. **Pump room enclosure:** **2-hr fire-rated** for high-rise (IBC §913.2.1) or buildings where pump serves a high-rise; **1-hr otherwise** (per NFPA 20 §4.12). Direct exterior access where feasible. Room kept **40 °F minimum**.
2. **Power supply (NFPA 20 §9.2 / §9.3 + NEC Article 695):** **reliable source** — utility-only is acceptable only if the source meets NFPA 20 §9.2.2 reliability test. Otherwise **two sources** (utility + on-site generator, or two utility services). Feeders **dedicated**, no overcurrent protection between source and controller other than the listed disconnect (NEC 695.4(B)).
3. **Churn / shutoff pressure:** ≤140% of rated. Pump curve must show 100% rated flow at ≥100% rated pressure and ≥150% rated flow at ≥65% rated pressure (NFPA 20 §4.8.2).
4. **Jockey pump:** sized to make up small leakage; cut-in pressure 10 psi below main pump start, cut-out at system pressure; piping per §4.27.
5. **Flow test fittings:** flow meter loop or test header. Verify discharge to safe location (storm drain not allowed to be over-pressured).
6. **Controller:** **listed for fire pump service** (UL, FM); transfer switch listed for fire pump service if generator backup; **Mark IIA / III / etc.** — verify listing matches motor type (electric vs. diesel).
7. **Diesel fuel:** **on-site fuel storage = ≥1 gal per HP plus 5%** (NFPA 20 §11.4.2). Day tank if remote storage. Fuel piping per NFPA 30/30A.
8. **Annunciation:** pump running, phase reversal, loss of phase, controller off-normal — annunciated at constantly attended location (fire command center for high-rise, building lobby otherwise).

---

## 5. Fire alarm (NFPA 72 + IBC §907) — top 12 checks

> **Edition note:** confirm with FMO whether the active CRP references **NFPA 72-2019** (typical for IBC 2021 reference) or **NFPA 72-2022**. Spacing / battery / ECS provisions are essentially the same; some CO and ECS sections updated in 2022.

1. **Where required (IBC §907.2):** by occupancy. Quick triggers: A — occupant load 300+; B — 500+ total or 100 above/below LOE; E — 50+ except small E with sprinklers and direct exit; F — 2 stories + 500 occ above/below; H — all H; I — all I; M — 500+ total or 100 above/below LOE; R-1/R-2/R-4 — most cases. **High-rise (§907.2.13) — always.**
2. **Initiating device spacing — smoke detectors (NFPA 72 §17.7):** 30 ft spacing on smooth ceilings, halve at walls (15 ft from walls) — but actually: **listed spacing varies by manufacturer** and can be reduced for beam ceilings, sloped ceilings (use Table 17.7.3.2.4.1), HVAC airflow >300 fpm. **In duct (§17.7.5):** required for HVAC >2,000 cfm (supply) or where serving >1 story.
3. **Heat detectors (§17.6):** spacing per listing (typically 50 ft on smooth ceiling). Reduced for high ceilings per Table 17.6.3.5.1. Verify rate-of-rise vs fixed-temp selection by environment.
4. **Notification appliance — visual (NFPA 72 Ch. 18) / ADA:** strobes per **§18.5** — Table 18.5.5.5.1 (room sizes vs candela: 20×20 ft = 15 cd wall; 30×30 = 30 cd; etc.). **Sleeping rooms = 110/177 cd intensity** at pillow level; **synchronization** required when more than 2 strobes are visible from one location.
5. **Notification — audible (§18.4):** **15 dBA above ambient or 5 dBA above max sustained 60 sec, whichever is greater**, throughout occupiable areas; **75 dBA at pillow** in sleeping rooms.
6. **Survivability of circuits (§24.4 / §12.4):** **Pathway Survivability Levels 0/1/2/3** — Level 3 (2-hr rated cable or in 2-hr enclosure) required for high-rise voice/ECS partial-evac systems. Verify the level called out matches the building height/use.
7. **Monitoring (§26.3):** central station, remote supervising station, or proprietary; signal transmission listed (DACT, IP, cellular). Verify two paths if required.
8. **Voice evacuation / EVACS:** required for **A-1, A-2, A-3, A-4 with occupant load >1,000** (IBC §907.2.1.1); **E with 100+ occ** (§907.2.3); **high-rise (§907.2.13.2)**; **covered malls + open malls (§907.2.20)**; **R-1 high-rise**. Live-voice mic at FCC.
9. **Mass Notification / ECS (NFPA 72 Ch. 24):** required where risk analysis shows need; DOD/federal-leased buildings often require it. Wide-area outdoor and in-building components. Coordinate with EVACS — ECS takes priority over fire alarm voice.
10. **Battery calculation (§10.6.10):** **24-hr standby + 5 min alarm (or 15 min for voice/ECS)** with all appliances at full alarm load. Two sets of batteries required if generator not provided. Verify spreadsheet shows current draws by device, derating factor (typically 1.2), and ambient temp factor.
11. **Elevator recall (NFPA 72 §21):** **Phase I recall** — smoke detectors at each elevator lobby (except lobbies with sprinkler), top of hoistway (if sprinklered), and machine room. **Phase II keyed control** in cab. Shunt-trip required where machine room sprinklered (ASME A17.1 + NFPA 72 §21.4).
12. **Smoke control interface (§23):** dedicated smoke-control panel; FACP provides input; sequence-of-operations matrix on plans; **fan damper end-switch confirmation** required, not just relay command. Required for atria, smoke-protected assembly seating, underground buildings, high-rise stair pressurization.

---

## 6. Means of egress (IBC Ch. 10, FP-relevant) — top 10 checks

1. **Occupant load (Table 1004.5):** A-2 unconcentrated 15 net, concentrated 7 net, standing 5 net; B 150 gross; M 60 gross (mercantile sales) / 300 gross (storage); E 20 net (classroom). Verify the architect didn't use gross where net is required.
2. **Egress width (§1005.3):** **0.2 in/occ stairways** (sprinklered with EVACS — 0.3 unsprinklered); **0.15 in/occ other components** (0.2 unsprinklered).
3. **Common path of egress travel (Table 1006.2.1):** B sprinklered = 100 ft, A = 75 ft, R-2 = 125 ft within unit. Don't confuse with travel distance.
4. **Dead-end corridor (§1020.5):** 20 ft generally, **50 ft for B/F/M/S/U sprinklered**.
5. **Travel distance (Table 1017.2):** B sprinklered = 300 ft, A sprinklered = 250 ft, H-1/H-2 = 75–100 ft, R-2 sprinklered = 250 ft.
6. **Number of exits + remoteness (§1007):** **two means** required when occ load exceeds Table 1006.3.3 limits or travel-distance/common-path limits. **Remoteness: ½ diagonal (1/3 with sprinklers + EVACS = §1007.1.1 exception).**
7. **Stair width (§1011.2):** ≥44" generally; 36" if total occ <50.
8. **Door swing & hardware (§1010):** swing in direction of egress where occ ≥50 or H occupancy. Panic hardware: A or E with ≥50 occ, H. Maximum unlatching force 15 lbf; opening force 5 lbf interior, 8.5 lbf exterior; closing force 30 lbf to set in motion.
9. **Exit discharge (§1028):** ≤50% of exits may discharge through lobby (sprinklered). Lobby separated by smoke partitions; direct path to public way.
10. **Smokeproof enclosures / pressurized stairs (§909.20 / §1023.11):** required for high-rise + underground >30 ft. Verify pressurization 0.10–0.35 in. w.c. across each door, with 1 door open; FACP integration.

---

## 7. Passive fire protection (IBC Ch. 7) — top 8 checks

1. **Fire-resistance ratings by construction type (Table 601):** memorize column headings — Type I-A (3-hr structural, 3-hr exterior bearing), I-B (2/2), II-A (1/1), II-B (0/0), III-A (1/2), III-B (0/2), IV-HT (HT/2), V-A (1/1), V-B (0/0). Most Fairfax commercial reno = II-B or II-A.
2. **Fire walls (§706):** continuous from foundation to/through roof; rating per Table 706.4 (3-hr typically; 2-hr for B). **Creates separate buildings** for area/height purposes.
3. **Fire barriers (§707):** rated assemblies for shafts, exit enclosures, exit passageways, incidental uses, fire areas, mixed-occ separation. Continuity §707.5: from floor to floor/roof slab.
4. **Fire partitions (§708):** corridors (§1020 — typically 1-hr; 0-hr in some sprinklered B), tenant separations in covered malls, dwelling unit separations (1-hr), R-1 sleeping unit separations.
5. **Smoke barriers (§709)** vs **smoke partitions (§710):** smoke barriers are rated (1-hr typical) and required for areas of refuge, smoke compartments in I-2, underground; smoke partitions are unrated but tight-to-deck-or-listed-ceiling.
6. **Penetrations (§714):** **through-penetration firestop systems = ASTM E814 / UL 1479**, listed for the assembly. **Membrane penetrations** per §714.4.2 (steel boxes ≤16 sq in spaced ≥24" OC, etc.). Plans must call out **UL system numbers (e.g., "UL System W-L-3047")** — reject "firestop per UL listing" without a number.
7. **Fire dampers / smoke dampers / combo (Table 717.5.1–717.5.4 + IBC §717):** fire damper at fire wall/barrier penetrations (1.5-hr or 3-hr rating to match), smoke damper at smoke barrier and air-handling system penetrations of corridors >1,000 cfm. **Combination fire/smoke damper** at smoke barriers that are also fire-rated.
8. **Fire doors (Table 716.1) + opening protectives:** wall-rating drives door rating: 4-hr wall → 3-hr door, 3-hr wall → 3-hr door, 2-hr wall → 1.5-hr door, 1-hr corridor → 20-min door (mostly with 1,296 sq in glazing limits). **NFPA 80** governs installation, clearances (≤¾" between door & frame at top/sides, ¾" at bottom), self-closing, no field modifications outside listing.

---

## 8. Special hazards

- **Commercial cooking (NFPA 96 + IFC §609 + IMC §507):**
  - **Type I hood** over all grease-producing equipment; UL 710 listed.
  - **Exhaust:** ≥500 fpm duct velocity (≥1,500 fpm historic — verify code edition); welded liquid-tight 16-ga black or 18-ga stainless duct; clearance to combustibles per NFPA 96 §4.2.
  - **Suppression: UL 300 listed wet-chemical** system (dry-chem no longer listed for restaurant cooking). Coverage of all appliances and plenum/duct. Manual pull at egress path 10–20 ft from cooking line, 42–60" AFF.
  - **Fuel/electric shutoff** on activation; gas valve mechanical reset.
  - **Make-up air** — IMC §508. ≥80% of exhaust except where balance achieved by transfer; tempered if winter design temp <35 °F.
  - **Grease duct light test** at acceptance (Fairfax practice — confirm with FMO).
- **Spray booths (IFC §2404 / NFPA 33):** ventilation 100 fpm cross-draft; sprinklers (auto closure or quick-response), suppression interlock with exhaust + ignition shutoff; bonding/grounding; explosion venting if applicable; Class I, Div 1/2 electrical zones around the booth.
- **Battery rooms / ESS (IFC §1207 — NEW in 2021, frequent in Fairfax):** Maximum stored energy thresholds (Table 1207.1.1: 20 kWh Li-ion before §1207.5/1207.7 kicks in fully); separation from other use groups (1-hr per §1207.7.1); ventilation per §1207.7.6 (or hydrogen detection for VRLA/wet-cell); deflagration venting; signage; UL 9540 listing for the ESS unit + UL 9540A test report for thermal runaway propagation. **Outdoor ESS** has its own setback rules (§1207.10).
- **Hazmat (IFC Ch. 50–67):** Use Table 5003.1.1(1)/(2) for MAQ vs control area; if exceeded → H occupancy. Common Fairfax triggers: server-room battery banks, lab solvents, pool chemical storage. Verify control-area count per floor (4 max ground level, decreasing upward), 1-hr fire barriers between control areas (sprinklered).
- **Solar PV (IFC §1204):** roof access pathways (3 ft along ridge, 4 ft setback for hip roofs <2/12 etc.); rapid shutdown (NEC 690.12); marking and labeling; smoke ventilation considerations; access for FD around array.
- **Generator/fuel oil (IFC §603 + NFPA 110):** day tank ≤60 gal in same room w/o separation; main tank in separate 2-hr room or outdoors; spill containment; vent piping to outdoors.

---

## 9. Fairfax FMO specifics

- **Operational permits (IFC §105.6, as amended):** required for activities that occur in operating buildings — places of assembly (>50 occ), open burning, hot work, hazmat above MAQ thresholds, flammable/combustible liquid storage, LP-gas, spraying/dipping, pyrotechnics/fireworks, tents over 900 sf or 50+ occ, automotive wrecking/repair, refrigeration systems above thresholds. **Verify the current Fairfax operational permit list** on the FMO site — Fairfax may add/modify per local amendment.
- **Installation permits (FMO):** fire alarm + detection, fire sprinkler, standpipe, fire pump, private fire service main (UG/AG), smoke control, fire protection supervisory, alternative extinguishing (clean agent / wet chem / dry chem), special locking arrangements, fuel storage tanks, **ERCES (in-building emergency radio communications enhancement system)**.
- **Tactical / pre-incident plans:** required for high-rise, large hazmat, unusual hazards, hospitals, malls. Fairfax FMO Special Operations branch coordinates. Plan format follows NFPA 1620 outline; site/floor plans with hydrant locations, FDC, FCC, riser locations, hazardous materials inventory, evacuation diagrams.
- **Knox Box (Fire Department Key Box):** **mandatory for all buildings except single-family**. Approved boxes: **Knox-Box Rapid Entry System (Knox Co.)** or **SupraSafe (Kidde)** — UL 1037 listed. Mounted at primary FD entrance (or entrance closest to fire control room). **Height: 42–54" above finished grade.** **Fire Command Center buildings: 15 sets of keys; all others: 3 sets.** Owner must immediately notify the local fire station when locks change.
- **Fire lane / fire apparatus access (IFC §503 + Fairfax PFM Ch. 9):**
  - Width **≥20 ft unobstructed** (exclusive of shoulders).
  - Vertical clearance **≥13 ft 6 in**.
  - All-weather surface, designed to support fire apparatus loading (see PFM tables for specific axle loads).
  - Turning radius and turnaround per PFM (no >150 ft dead-end without approved turnaround).
  - Marking + signage per PFM and county standard.
  - Required within 150 ft (most occupancies) / 250 ft (R-3 sprinklered or fully sprinklered I-A/I-B per IFC §503 exceptions) of all portions of the exterior of the building.
  - Gates: emergency override + Knox key switch; security gates per §503.6.
- **Hydrant spacing:** per PFM — generally ≤500 ft for commercial in Fairfax (verify exact value in current PFM Ch. 9). FDC must be within 100 ft of a hydrant.
- **FDC threads — Fairfax / NoVA:** historically standardized on **5" Storz with 30° rocker lugs** (verify exact spec with FMO at intake — local-only amendment).
- **Required submittal items beyond IFC base (FMO commercial intake, eff. 2024-01-18):**
  - Completed **Plan Review Submission Checklist – Commercial** (signed by RDP in Responsible Charge). Applies to: new buildings, additions >1,000 sf, change-of-use ≥5,000 sf, **Level 2 alterations** per Virginia Existing Building Code.
  - Cover sheet with code analysis: occupancy, construction type, allowable area/height calc, sprinkler/standpipe/alarm matrix.
  - Riser diagrams (sprinkler + standpipe + alarm) on the FP set, not buried in MEP.
  - Manufacturer cut sheets / technical data sheets for all listed equipment.
  - Hydraulic calculation packet (sprinkler).
  - Battery calculation (alarm) + voltage drop calc on NAC circuits.
  - Reflected ceiling plan correlation (sprinkler heads vs. lights/diffusers).
  - Site plan with hydrant locations + FDC + fire lane + Knox box location.
  - For ESS: UL 9540 listing + UL 9540A test summary.
  - For ERCES: signal survey or design study.

---

## 10. Submittal completeness checklist — what FP reviewers reject on first pass

Reject (or comment with required-correction) when ANY of the following are missing or inconsistent:

- [ ] **Code analysis cover sheet** — occupancy, construction type, area/height, sprinkler/alarm matrix.
- [ ] **Hydraulic calculation packet** for any new/modified sprinkler system, including water supply test data ≤12 months old.
- [ ] **Manufacturer cut sheets** for all sprinklers, alarm devices, hood suppression nozzles, ESS units.
- [ ] **Riser diagram** (sprinkler + standpipe + alarm) — must show floor-by-floor connections and zone valves.
- [ ] **Battery calculation** for alarm — 24-hr standby + 5 (or 15 for voice) min alarm with 1.2 derating.
- [ ] **Candela schedule / NAC schedule** for visual notification — strobe candela by room, sync circuits identified.
- [ ] **Occupant load summary** keyed to floor plan (rooms / functional areas with code basis from Table 1004.5).
- [ ] **Reflected ceiling plan correlation** — sprinkler layout matches RCP; no obstruction conflicts with diffusers/lights/beams.
- [ ] **UL system numbers** for through-penetration firestopping (e.g., "UL W-L-3047") on each rated wall/floor section.
- [ ] **Fire damper & smoke damper schedule** keyed to architectural rated wall plan, with rating + access door note.
- [ ] **Fire door schedule** with door rating, frame rating, hardware listing, glazing area, NFPA 80 compliance note.
- [ ] **FDC + hydrant + fire lane + Knox box location** shown on the site plan.
- [ ] **Sequence of operations** matrix (alarm → HVAC shutdown, smoke control mode, elevator recall, door release).
- [ ] **Pump curve + power source description** for fire pump submittals.
- [ ] **Smoke control rational analysis** if applicable (atria, high-rise stair pressurization).
- [ ] **Egress diagram** for each floor with travel distances, common path, dead-end measurements.
- [ ] **RDP-in-responsible-charge stamp** on the FP set (Virginia license; for PR work the Fire Protection PE seal applies — VA accepts FP PE).
- [ ] **Fairfax Plan Review Submission Checklist** signed (where required by 2024 rule).
- [ ] **Operational permit list** identified where applicable (assembly, hot work post-CO, hazmat, etc.).

---

## Quick reference table — codes & editions

| Topic | Standard | Edition (verify with FMO) |
|---|---|---|
| Building / fire-resistance / egress | IBC | 2021 (via VCC / USBC) |
| Operating fire prevention | IFC | 2021 (via VSFPC) |
| Sprinklers | NFPA 13 / 13R / 13D | 2019 (per IBC 2021 Ch. 35 reference) |
| Standpipe | NFPA 14 | 2019 |
| Wet chem / restaurant cooking | NFPA 17A + NFPA 96 | 2017 / 2021 |
| Fire pump | NFPA 20 | 2019 |
| Private fire service main | NFPA 24 | 2019 |
| ITM (existing systems) | NFPA 25 | 2020 |
| Electrical | NFPA 70 (NEC) | 2020 |
| Fire alarm | NFPA 72 | 2019 (confirm; some packages 2022) |
| Fire doors | NFPA 80 | 2019 |
| Smoke control | NFPA 92 | 2018/2021 |
| Cooking equipment | NFPA 96 | 2021 |
| Life safety (reference only — not adopted by VA) | NFPA 101 | 2021 |
| Clean agent | NFPA 2001 | 2018/2022 |
| Local administration | VSFPC (VA amendments) | 2021 |
| Local administration | Fairfax County Fire Prevention Code amendments + PFM Ch. 9 | current |

---

## Day-of-training reminders

- Bring a printed copy of this cheat sheet, the **Fairfax Commercial Plan Submission Checklist**, and a tabbed IBC 2021 + IFC 2021.
- The **2018 CRP v2** (Feb 2024) is still the public guidance package — confirm at training whether 2021 CRP is now active.
- For any item you're not 100% sure about → write **"verify with FMO"** in the review comment, not a fabricated citation. This is the same discipline that keeps BCC inspection reviews defensible.
- FMO Engineering Plans Review: **703-246-4806 / fire.engplansreview@fairfaxcounty.gov**. Fire Protection Systems Branch (permits/inspections): **703-246-4821**.

— End of cheat sheet —
