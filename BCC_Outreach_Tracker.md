# BCC Outreach Tracker

**Last updated:** 2026-05-01 (Renovations Expert Inc. partner intro send)
**Maintainer:** Update this file every time you send/get-replied/win/lose. The auto-CSV (`bcc_proposal_sent_log.csv`) is the machine record; this is the curated human view. They should agree — if not, run `python core_tools/bcc_inbox_audit.py` for IMAP ground truth.

**Sources:**
- IMAP audit (`core_tools/bcc_inbox_audit.py` + `Pending_Approval/_audit_data.json`) — covers since 2026-02-01
- `.send_*.marker` files — one-off batch send guards
- `bcc_proposal_sent_log.csv` — auto from `send_followup_proposals.py` / `send_cw_*.py` (04-24 onward)
- `Pending_Approval/Outbound/*-SENT.md` — renamed drafts (post-send marker)

---

## Status Legend
| Code | Meaning |
|---|---|
| 🟢 SENT | Initial proposal/email sent, ≤7 days, no reply yet |
| 🔵 FOLLOWUP_SENT | Initial + ≥1 followup sent, still awaiting reply |
| 🟡 UNDER_REVIEW | Client replied with engagement (asking for proposal, "estimator will contact", forwarded to right contact) |
| 🟣 CONFIRMED | Won the bid / contract signed / signed copy returned |
| 🔴 LOST | Declined / project went elsewhere / explicit "we lost it" |
| ⚪ DRAFT | In `Pending_Approval/Outbound/` root, not yet sent |
| ⚠️ DEAD_CODE | Hardcoded in send script but never actually sent (no IMAP record since 02-01) |

---

## 1. BC Bidding Proposals (Invited Bids w/ PDF attachment)

### IMAP-confirmed sends (April 2026 batch)
| Status | Project | Client | Contact | Email | First Sent | Notes |
|---|---|---|---|---|---|---|
| 🟢 SENT | AIA Headquarters Renewal (1735 New York Ave NW) | Turner Construction | Akilah Miles | amiles@tcco.com | 2026-04-23 | followup due 2026-04-30 |
| 🟢 SENT | Room Renovation DC Div 02 Demolition (732 N Capitol NW) | G3 Contracting | Cameron McBride | cmcbride@g3-contracting.com | 2026-04-23 | |
| 🟢 SENT | GPO NARA 4th Floor Turnkey Buildout | Capital Trades | Esthuardo Palma | epalma@capitaltradesva.com | 2026-04-23 | |
| 🟢 SENT | 1724 F Street NW Floor 1 & 3 Renovations | J&J Construction | Ian Barry | ibarry@jandjconst.net | 2026-04-14 | (IMAP confirmed — file `-SENT.md` 已 rename) |
| 🟢 SENT | Interior Renovations Multi-Floor | J&J Construction | Ian Barry | ibarry@jandjconst.net | 2026-04-23 | sent ×2 same subject |
| 🟢 SENT | Neko Health Anthem Row (700 K St NW) | Sachse Construction | Jonathan Lopatin | jlopatin@sachse.net | 2026-04-22 | **DUPLICATE-SEND incident** — apology sent same day |
| 🟢 SENT | Panda Express Navy Yard (1247 1st St SE) | Parkway Construction | Jeff Whiting | jwhiting@pkwycon.com | 2026-04-23 | |
| 🟢 SENT | GPO NARA 4th Floor Renovation | PWC Companies | Nicole Erdelyi | nerdelyi@pwccompanies.com | 2026-04-23 | (different from WIT below) |
| 🟢 SENT | 427 Ridge St NW Residential Renovation | Redux LLC Designs | (Redux) | reduxllcdesigns@gmail.com | 2026-04-21 | |
| 🟢 SENT | LaserAway Washington DC (1427 P St NW) | Horizon Retail | Sandra R | sandrar@horizonretail.com | 2026-04-22 | replied 04-23 → see UNDER_REVIEW below |
| 🟢 SENT | NHM Sanitary & Storm Systems Upgrade | Guardian Construction | Travis Boren | travis.boren@guardiangc.net | 2026-04-22 | |
| 🟢 SENT | US GPO QCIM Room Renovation + JBAB B94 Breaker (combo recipient) | Desbuild | Natasha Solis | natasha.solis@desbuild.com | 2026-04-23 | replied "Received. Thanks." (just receipt) |

### Older sends (pre-02-01, deduced from 04-27 followups)
| Status | Project | Client | Contact | Email | Last Action |
|---|---|---|---|---|---|
| 🔵 FOLLOWUP_SENT | Diner Bar at JW Marriott (1331 Pennsylvania NW) | Whiting-Turner | Michael Cecchini | michael.cecchini@whiting-turner.com | followup 2026-04-27 — earlier reply: "yes received bid, hoping for owner feedback" + 04-27 OOO until 04-28 |
| 🔵 FOLLOWUP_SENT | JW Marriott Restaurant + Diner Bar Rebid | Whiting-Turner | Seydou Tounkara | seydou.tounkara@whiting-turner.com | followup 2026-04-27 — earlier reply confirmed receipt (was in spam folder) |
| 🔵 FOLLOWUP_SENT | Insomnia Cookies + Joe & The Juice Union Station | Built With Benchmark | Matt | matt@builtwithbenchmark.com | followup 2026-04-27 — earlier reply: "apology for big lapse, busy" |
| 🔵 FOLLOWUP_SENT | Washington Improv Theater (WIT) Interior Alteration | PWC Companies | Nicole Erdelyi | nerdelyi@pwccompanies.com | followup 2026-04-27 — earlier reply: "Received - thanks!" (just receipt) |
| 🔵 FOLLOWUP_SENT | 3050 K St NW 3rd & 4th Floors | Winmar Construction | T Plum | tplum@winmarconstruction.com | followup 2026-04-27 — no prior reply |
| 🔵 FOLLOWUP_SENT | Kolmac Expansion (1025 Vermont Ave NW) | HBW Construction | J Lauer | jlauer@hbwconstruction.com | followup 2026-04-27 — no prior reply |
| 🔵 FOLLOWUP_SENT | Rivian Flagship Renovation (1100 New York Ave NW) | Sachse Construction | B Miller | bmiller@sachse.net | followup 2026-04-27 — no prior reply |
| 🔵 FOLLOWUP_SENT | EagleBank Branch (2001 K St NW) | Doyle Construction | T Liang | tliang@doyleconco.com | followup 2026-04-27 — no prior reply |
| 🔵 FOLLOWUP_SENT | 4900 Georgia Ave NW | Victor (owner) / RM Tax | Melissae | melissae@rmtax.services | followup 2026-04-27 — no prior reply |
| 🔵 FOLLOWUP_SENT | 1154 4th St NE Rear Stairs Installation (+ 6024 8th) | Alvin Gross (owner) | Alvin Gross | agrossjr@aol.com | followup 2026-04-27 — no prior reply |
| 🔵 FOLLOWUP_SENT | Washington Endometriosis (5225 Wisconsin Ave NW) | HBW Construction | J Williams | jwilliams@hbwconstruction.com | original sent 2026-03-04, followup 2026-04-27 — no reply |
| 🔵 FOLLOWUP_SENT | 1425 Rhode Island Ave NW | SEI | service@seiwork.com | followup 2026-04-27 — no prior reply |

### UNDER_REVIEW — engaged replies needing Kyle's attention
| Status | Project | Contact | Last Reply | Snippet |
|---|---|---|---|---|
| 🟡 UNDER_REVIEW | LaserAway DC | sandrar@horizonretail.com | 2026-04-23 | "Thank you for taking the time to provide Horizon Retail Construction with your proposal. If the estimator has any questions he will contact you." → wait for estimator |
| 🟡 UNDER_REVIEW | 3109 Oak Hill Modular (Bldgs 14 & 15) | eric@aandeconstructionllc.com | 2026-04-03 | "I wanted to follow up with the proposal per our conversation. Please advise." + permit drawings shared 03-05 + asking for sprinkler price proposal 04-01 → already followed up 04-27 |
| 🟣 CONFIRMED | Maher Residence Addition + MSA | teddy@preciseengineer.com | 2026-04-16 | Signed copy returned — **Kyle confirmed 2026-04-28** |
| 🟡 UNDER_REVIEW | 1522 Rhode Island Ave NE Plan Review | nery@rexfield.us | 2026-04-17 | "Kyle see attached" → review attachment |
| 🟡 UNDER_REVIEW | Souvenir HQ 917 F ST NW Permit B2603010 | chloenguyen10@gmail.com | 2026-02-06 | "I submitted the permit application... Let me know what the process" → may be stale |
| 🟡 UNDER_REVIEW | Deanwood Metro Station Redevelopment | raymond@nixdevco.com | 2026-02-20 | "Will hold contact info as we go through procurement" → long-term lead |

### LOST — explicit decline / dead
| Status | Project | Contact | Last Reply | Snippet |
|---|---|---|---|---|
| 🔴 LOST | House Bar (300 Morse St NE) | pwhite@infinitybuildinginc.com | 2026-02-20 | "We lost that one" / "We lost that job." |
| 🔴 LOST | Former Fox 5 Mixed-Use | lcaudle@hickokcole.com | 2026-04-24 | "Sorry this is no longer our project" |

### LOST — pre-02-01 (Kyle confirmed 2026-04-28: "二月份时候的东西了应该是发过了，不用看了")
| Status | Project | Client | Contact | Notes |
|---|---|---|---|---|
| 🔴 LOST | 20 F St NW Suite 550 Tenant Renovation | HBW Construction | Angel Colon (acolon@hbwconstruction.com) | Sent pre-02-01 (before audit window); no follow-up traction. Closed. |
| 🔴 LOST | St. Joseph's on Capitol Hill Phase I | Keller Brothers | Alex Pauley (apauley@kellerbrothers.com) | Same — pre-Feb send, no traction. Closed. |

---

## 2. CW Cold Outreach (ConstructionWire pipeline development — NO PDF, intro only)

### 04-28 batch (sent today via `send_cw_batch_20260428.py`)
| Status | Lead Company | Contact | Email | Sent | Followup Due |
|---|---|---|---|---|---|
| 🟢 SENT | Carmel Partners | Ronnie Gibbons | rgibbons@carmelpartners.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | Crescent Heights | Manuel Zacarias | mzacarias@crescentheights.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | Felice Development Group | Rick Felice | rick@felicedevelopmentgroup.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | GTM Architects | James Myers | jmyers@gtmarchitects.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | GTM Architects | Rosana Torres | rtorres@gtmarchitects-dc.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | GTM Architects | Susan Mentus | smentus@gtmarchitects-dc.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | MILLER | Mike Valazak | mvalazak@miller.group | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | RedBrick LMD | Joel Causey | jcausey@redbricklmd.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | RedBrick LMD | Paul Elias | pelias@redbricklmd.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | Transwestern Companies | Larry Serota | larry.serota@transwestern.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | Transwestern Companies | Peter Prominski | peter.prominski@transwestern.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | WC Smith | Chris Smith | csmith@wcsmith.com | 2026-04-28 | 2026-05-09 |
| 🟢 SENT | idGROUP | Carry McLain | cmclain@idgroupdallas.com | 2026-04-28 | 2026-05-09 |

### Earlier CW followups in flight (audit shows >1 send + followup type)
- `tony@wkmsolutions.net` (Howard Hospital), `mrw@winstanleyarchitects.com` (Poplar Point), `salexander@tortigallas.com` (Former Fox 5 — see also 🔴 LOST above), `mtamaro@thorntontomasetti.com` (Burnham Place), `ahayes@rappaportco.com` (ABA Centers Skyland) — all 🔵 FOLLOWUP_SENT 2026-04-23
- `dbowers@lfjennings.com` (Dalian Office Reno) — 🟡 UNDER_REVIEW, replied "See attached" 04-24
- `lcaudle@hickokcole.com` — 🔴 LOST (see above)
- (Full list of 113 CW intros in `Pending_Approval/_audit_report.md`)

---

## 3. Other Outbound

| Status | Project | Contact | Email | Sent | Type | Notes |
|---|---|---|---|---|---|---|
| 🟢 SENT | MedStar Georgetown Cyberknife Equipment Addition | Senit Hailemariam | senit.t.hailemariam@gunet.georgetown.edu | 2026-04-27 | Intro (cold) | Reached after Shenelle/Basani forwarded — was Shenelle (PCCM-4Main, no Cyberknife support) → Basani (Interventional Pulmonology) → Senit |
| 🟢 SENT | Renovations Expert Inc. (Building & Design Construction) — partner intro | Aday Galindo (boss) + Edwin Ferman + Juancarlos Lazarte | builddesigninc@gmail.com (CC: Edwinbuilddesigninc@gmail.com, info@mechanicalelectricalinc.com) | 2026-05-01 | Intro (warm partner) | Sent BCC Introduction + Capabilities Statement + Residential Pricing PDFs. Boss name "Daw" → verified as Aday Galindo via BuildZoom/Houzz/D&B. Roster at `Partners/Renovations_Expert_Inc.md`. |
| 🟢 SENT | DOB NOI 1522 Rhode Island Ave NE | (DOB filing dob@dc.gov) | dob@dc.gov | 2026-04-17 | Regulatory submittal | Auto-acks on 02-04 / 02-06 / 04-17 / 04-24 (DC ticketing system) |

---

## 4. Active Drafts (in `Pending_Approval/Outbound/` root, not yet sent)

| Status | File | Project | Client | Contact | Decision Needed |
|---|---|---|---|---|---|
| ⚪ DRAFT | `Email_427_Ridge_St_NW_Donovan_20260421_1522.md` + `Proposal_Draft_427_Ridge_St_NW_-_Residential_Renovation.md` | 427 Ridge St NW Residential Reno (Owner-side) | Daniel Donovan (owner) | — | **Note:** GC-side already sent to reduxllcdesigns@gmail.com 04-21 (Section 1). This is the owner-side parallel pitch. |
| ⚪ DRAFT | `Email_Harkins_Vendor_Reapply_20260422_1609.md` | Harkins Vendor Reapply | Harkins | — | Vendor onboarding form (not a project proposal) |

---

## 5. Archived

- `Pending_Approval/Outbound/_obsolete_already_sent_20260428/` — 27 files: junk template `.md` drafts whose polished versions were sent via `send_*.py` one-off scripts (04-22/04-23). Kept for audit trail only.
- `Pending_Approval/Outbound/_archived_stale_20260428/` — 9 files: drafts >4 weeks old or with no contact (1300 Girard, 3109 Oak Hill ×2 modular original drafts, Washington Endometriosis original draft, 5407 Georgia, Washington Improv Theater). NOTE: Endometriosis + 3109 Oak Hill DID get sent (different drafts) — see Section 1 followup table.
- `Pending_Approval/Outbound/_archived_stale_20260427/` — earlier batch archived 04-27.

---

## 6. Quick Stats (post-audit, since 2026-02-01)

- BC Bidding proposals sent: **23 unique** (11 in April batch + 12 older deduced from followups; excludes self-test typo to caoyueno5@gmail.cm)
- CW intros sent: **113** (per audit `cw_intro` type)
- Followups sent: **115** (per audit `followup` type)
- Other outbound: **55** (intros, replies, regulatory)
- Total replies received: **41** (38 unclear + 3 auto/OOO; 0 explicit interested, 0 explicit declined per classifier)
- Bucket E (no-reply, followup-eligible): **153 recipients**

---

## 7. How to Update This File

1. **After every send**, edit the relevant table row's status code and date. If it's a new project, add a new row.
2. **When client replies**, flip status:
   - Engaged ("send proposal", "let me forward to estimator", forwarded to right contact) → 🟡 UNDER_REVIEW + add the reply snippet
   - Won / signed → 🟣 CONFIRMED
   - Decline / lost → 🔴 LOST
3. **Followup cadence** = 4 days (per CLAUDE.md). When followup goes out, update last-action column + status to 🔵.
4. **Once a quarter** (or when Section 1 grows >50 rows), archive 🔴 LOST and 🟣 CONFIRMED into `BCC_Outreach_Archive_YYYYQq.md`.
5. **Re-run audit** (`python core_tools/bcc_inbox_audit.py`) before any major review to catch drift between this file and IMAP truth.
