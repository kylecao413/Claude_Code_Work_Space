# 03a — Structural Plan Peer Review Scan-Order Cheatsheet

**KCY Engineering Code Consulting LLC** · 2021 VCC Ch 16-17 · Fairfax County
**Scope reminder:** Peer review only. Fairfax retains official structural review + structural shop drawing review. Our review minimizes their rejection comments.

> Structural items are filled into the **Building** PRR §J (New Commercial) and the **Statement of Special Inspections** form. There is no separate Structural PRR in Fairfax's set.

---

## Round 1 — 5-min binary check

- [ ] Statement of Special Inspections (SSI) form attached, sealed by Structural Engineer (PE), pages 2-3 fully marked yes/no
- [ ] Structural calculations sealed + dated by VA-licensed SE
- [ ] Foundation plan + framing plan + connection details all on plans
- [ ] **Fairfax design loads** present: Pg=25 psf, V=90 mph (Vult=115), Ss=0.129, S1=0.053
- [ ] Geotech report (sealed, VA RDP) if soil > 2,000 psf or any deep foundation

---

## Round 2 — Sheet-by-sheet

### S0.0 — General Notes / Code Summary (3 min)
- [ ] Code editions: 2021 VCC + 2018 IBC (referenced) + ASCE 7-16 + ACI / AISC / NDS as applicable
- [ ] Risk Category stated
- [ ] Live loads listed by occupancy per Table 1607.1
- [ ] Snow: Pg, Pf, Ce, I, Ct + drift Pd / W if applicable; **Pg = 25 psf** Fairfax
- [ ] Wind: V, Vt, Vasd, Risk Cat, Exposure, GCpi, design pressure for components/cladding; **V=90 mph (40 m/s), Vult=115 mph (51 m/s)** Fairfax
- [ ] Seismic: Risk Cat, IE, mapped + design spectral response (Ss/S1/SDS/SD1), Site Class, Design Cat (SDC), SFRS, design base shear, Cs, R, analysis procedure; **Ss=0.129, S1=0.053** Fairfax
- [ ] Allowable bearing pressure noted + matches geotech
- [ ] Material strengths: f'c, fy, Fb, etc.

### S1.x — Foundation Plan (4 min)
- [ ] Footing schedule (size, depth, reinforcement)
- [ ] Column schedule
- [ ] Foundation plan dimensioned, gridded, matches arch footprint
- [ ] Min frost depth 24" (Fairfax) for footings
- [ ] Imaginary lot lines + average grade plane (multi-building lots)
- [ ] Deep foundations (helical piles, aggregate piers, driven piles, caissons, augercast):
  - [ ] Geotech report covers area
  - [ ] Lateral/stability/settlement/group-effect analysis
  - [ ] Plan note: manufacturer, model, size, length, shaft dia, bearing plates count/size/thickness
  - [ ] Allowable axial design load per VCC §1810.3.3
  - [ ] Noted as subject to special inspections per VCC §1810.3.5.3.3
- [ ] Helical piles per VCC §1810
- [ ] Aggregate Pier Intermediate Foundation: ICC-ES eval report + design details + soil report + on SSI

### S2.x — Framing Plans (4 min)
- [ ] All structural members shown with sizes + sections + relative locations dimensioned
- [ ] Floor framing plan + roof framing plan
- [ ] Column centers + offsets dimensioned (§1603.1)
- [ ] Connection / attachment details (welds, bolts, plates) (§109.3)
- [ ] Mezzanine/equipment platform framing if applicable

### S3.x — Sections + Details (3 min)
- [ ] Wall sections + key details
- [ ] Beam-to-column connections
- [ ] Floor-to-wall, roof-to-wall details
- [ ] Lateral-system details (braced frame, moment frame, shear wall)
- [ ] Diaphragm details

### Trusses + Pre-Engineered + Special (2 min)
- [ ] Truss Plan Cover Sheet (`trusscvr.pdf`) + truss shop drawings (or deferred-submittal note)
- [ ] Sealed by truss design engineer
- [ ] Pre-fab building: calcs + structural details for entire framing
- [ ] Storage racks > 12' height: calcs + framing + anchorage; subject to special inspection per ICC §2209 + RMI/ANSI MH 16.1
- [ ] HVAC equipment attachment detail with calc (location relative to structural members; angles, channels, rods, bolts, welds)

### Statement of Special Inspections (5 min — county form)
- [ ] Form `sip_ssi.pdf` complete
- [ ] Page 1 — project info filled
- [ ] Pages 2-3 — every item marked Yes or No (no blanks)
- [ ] Sealed + signed by Structural Engineer
- [ ] Special Inspections meeting required prior to permit issuance — note on plans
- [ ] Items typically requiring SI: deep foundations, soils, concrete, masonry, steel, cold-formed steel, wood, EIFS, anchorage to concrete, fireproofing, smoke control, post-installed anchors, storage racks, helical piles, aggregate piers, fire-rated assemblies, structural observation per §1704.6.1

### Structural Observation (§1704.6.1, if triggered)
- [ ] SE submits written statement to Building Official identifying frequency + extent of structural observation

### Cross-discipline cross-checks
- [ ] HVAC equipment attachment detail with structural calcs (matches mechanical roof plan)
- [ ] Industrialized building: foundation + tie-downs per manufacturer's recommendations (13 VAC 5-91)

---

## Round 3 — Output

For every FAIL, internal note → if true deficiency → client log row (Discipline = "Structural"). Cross-reference Building deficiency log if multi-discipline.

**Time budget:** ~30 min for tenant interior reno (rare structural scope) / ~75 min for new commercial.
