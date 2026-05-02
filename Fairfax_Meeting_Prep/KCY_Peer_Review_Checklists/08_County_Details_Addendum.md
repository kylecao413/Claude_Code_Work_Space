# 08 — County Details Addendum (Building Sub-Scope)

**KCY Engineering Code Consulting LLC** · Fairfax County
**Scope:** Pre-approved architectural plans Fairfax provides for: Decks, Finished Basements, Carport Enclosures, Retaining Walls. These can be used **in lieu of** a separate architectural plan submission during permit application.

This is an **addendum to `01b` Building**, not a standalone trade. When a project's scope falls under a county detail, the architect can submit the County's pre-approved drawing instead of producing one. Our job is to verify they followed the County detail.

---

## When this applies

- **Decks** — residential decks (typically R-5)
- **Finished Basements** — residential below-grade habitable finish-out
- **Carport Enclosures** — converting open carport to enclosed garage / storage
- **Retaining Walls** — when within County-detail scope (typically up to a height limit; over the limit triggers separate sealed structural design)

If the actual scope **exceeds** what the County detail covers (e.g., deck cantilever beyond standard span, finished basement with unconventional egress, carport enclosure with HVAC additions, retaining wall taller than detail allows), the architect must produce a custom sealed plan — the County detail no longer suffices.

---

## How to review when County Detail submitted

For each of the 4 detail types, the workflow is the same:

### Step 1 — Verify scope match
Open the County detail PDF (in `County_Details/<type>/`):
- Is the project scope fully within what the detail covers (height, span, span-to-depth, materials, location)?
- If yes → proceed to Step 2
- If no → custom sealed plan required; flag as deficiency

### Step 2 — Verify architect referenced the detail correctly
- Drawing references the County detail by name + revision date
- Architect did not modify the County detail (modifications void it)
- Site-specific items (location, dimensions, soil/grade context) added separately + sealed

### Step 3 — Verify site-context items are still met
- Setback compliance (zoning)
- Easement clearance
- Egress for finished basements (window well, sized opening, ladder/steps if required)
- Frost depth for footings (24" min Fairfax)
- Drainage / surface water management for retaining walls
- Backfill requirements + compaction notes

### Step 4 — Output
Treat any failure as a Building deficiency and log under Discipline = "Building" with the sub-context noted (e.g., "Decks — County Detail compliance").

---

## Per-detail quick checks

### Decks (`County_Details/Decks/deck-details.pdf`)

- [ ] Deck size + height within detail's allowable range
- [ ] Ledger attachment to existing structure per detail (lag bolt or through-bolt + flashing)
- [ ] Joist span + spacing per detail's table
- [ ] Beam span per table
- [ ] Footing size + frost depth (24" Fairfax)
- [ ] Guard ≥ 36" residential / per detail
- [ ] Stair handrail + graspability
- [ ] Live load 40 psf
- [ ] Structural lateral bracing (knee brace or lateral connection) per detail

### Finished Basements (`County_Details/Finished_Basements/basement-details.pdf`)

- [ ] Egress window meets size + sill height (typically 5.7 sq ft + 24"H + 20"W; sill ≤ 44" AFF)
- [ ] Window well dimensions + ladder/step if required
- [ ] Smoke + CO alarms per VRC
- [ ] Furnace / water heater room separation per detail
- [ ] Stair construction + handrail
- [ ] Insulation R-values per VRC / VECC
- [ ] Vapor barrier
- [ ] Sump pump if applicable

### Carport Enclosures (`County_Details/Carport_Enclosures/carport_details.pdf`)

- [ ] Existing carport structure adequate for new enclosure loads
- [ ] Wall framing per detail (stud size + spacing)
- [ ] Header sizes per detail
- [ ] Garage door if applicable
- [ ] Fire separation between garage and house (if attached)
- [ ] R-value insulation per VECC
- [ ] If converting to habitable space: egress + light + ventilation per VRC

### Retaining Walls (`County_Details/Retaining_Walls/retaining-wall-details.pdf`)

- [ ] Wall height within detail's allowable range (typically 4' or 6' max)
- [ ] Soil type matches detail's design assumption
- [ ] Footing size + reinforcement per detail
- [ ] Drainage behind wall (gravel + perforated pipe)
- [ ] Setback from property line + structures
- [ ] If wall > detail's max height OR surcharge load (driveway, slope above) → custom sealed structural design required (separate permit)

---

## Companion files

- `00_KCY_Deficiency_Log_Template.docx` — log entries under Discipline = "Building"; reference the detail type in observation text (e.g., "Deck framing exceeds County detail allowable joist span...")
- `01b_Building_Full_Reference.md` — main Building checklist; this addendum is a sub-scope branch
