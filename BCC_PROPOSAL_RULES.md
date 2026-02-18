# BCC Proposal Generation – Mandatory Rules (No Exceptions)

These rules are derived from the Critical Failure Report and screenshot corrections. **Every proposal must follow them.**

---

## 0. Scraping / BuildingConnected – Setup & Correct Methods

### BC Self-Login Requirements

To auto-login to BuildingConnected, add these keys to `.env`:
```
BC_EMAIL=your-bc-login-email@example.com
BC_PASSWORD=your-bc-password
```
Script: `bc_scrape_project.py` reads these, navigates to `https://app.buildingconnected.com/login`,
fills the form, saves cookies to `.buildingconnected_cookies.json`, then scrapes the project page.

**URL format for project pages:**
`https://app.buildingconnected.com/opportunities/<PROJECT_ID>/info`

**Workflow:** User pastes BC project URL in Telegram → sends `/save` → Claude reads ACTIVE_TASK.md
→ runs `bc_scrape_project.py <url>` → scrapes all fields → generates proposal draft.

**If self-login fails (2FA / SSO):** Agent opens headful browser (visible), sends Telegram message
asking user to log in remotely or from phone screen-share. Script waits up to 5 min for login,
then proceeds to scrape.

### Scraping – Recorded methods (overwrite when confirmed):

- **Project Description / Exhibit A:** *(To be confirmed — run bc_scrape_project.py and update here with selector found.)*
- **Client name / GC:** *(To be confirmed with live page.)*
- **Address / Location:** *(To be confirmed with live page.)*
- **Attention / Contact:** *(To be confirmed — check bid form "To:" or overview "Invited by".)*

**Protocol:** When the agent finds the correct selector for any field, immediately update this file. Delete the "To be confirmed" line and replace with the exact selector/step.

---

## 0-B. Proposal Format: Per-Visit vs. Detailed Estimation

**DEFAULT RULE: Use Per-Visit ("Flat Rate per Visit") format for most projects.**

Per Kyle (2026-02-17): For small/standard projects and when the drawing set is not yet available,
send a per-visit proposal. The invoice is based on actual visits completed.

**Per-Visit proposal wording (use in Exhibit C / fee section):**
> "Inspection Services: Flat rate of $[PRICE]/visit, per discipline combo inspection.
> Total invoice will be based on actual number of visits completed."

**When to use Per-Visit:**
- Small tenant renovations (< ~5,000 SF)
- Projects where full permit drawings are not yet received
- Any project needing immediate/quick submission
- First-contact proposals before permit set is issued

**When to do full estimation (visits × scope breakdown):**
- Large projects (> 5,000 SF, multi-trade)
- Projects where Kyle has reviewed the drawing index
- Repeat clients where scope is well-understood

**Checklist addition for Per-Visit proposals:**
- [ ] Exhibit C states "flat rate per visit" and "invoice based on actual visits"
- [ ] No fabricated visit count breakdown (keep simple: 1 line, $/visit)
- [ ] Estimated total = $/visit × conservative estimated visits (note: estimate only)

---

## 1. Client Name (from BuildingConnected Overview)

- **Source:** The **"Client"** / **"Client Name Company Name"** field on the BuildingConnected project **Overview** tab. Do NOT use the project name or owner name as the client.
- **For "St. Joseph's on Capitol Hill – Phase I":** Client is **"Keller Brothers - Keller Brothers Special Projects"** (Bid Form shows "To: AP Alex Pauley … Keller Brothers"). Use **"Keller Brothers"** or the full name as shown on BC Overview.
- **Never use:** "Sample Client", "St. Joseph's on Capitol Hill" (as client—that is project/site context), "Cox & Company, LLC", **"Insomnia Cookies" / "Insomnia Cookies Renovation"** (wrong project name on cover or body), or any placeholder or name from another project.

---

## 2. Attention / Contact Person

- **Source:** BuildingConnected Overview or Bid Form **"To:"** recipient.
- **For St. Joseph's:** **Alex Pauley** (AP Alex Pauley), Title as shown; email **apauley@kellerbrothers.com**.
- **Never use:** "Bryan Kerr" or any contact from a different project or template. If the template contains a wrong name, replace it with the actual BC contact.

---

## 3. Project Address

- **Source:** BuildingConnected Overview **"Location (Address)"**.
- **In-document format:** Use **concise** address only: **"313 2nd Street Northeast, Washington, DC 20002"**. Do **not** add "United States of America" or a duplicate "Washington DC" after the zip.
- **Never use:** "701 Monroe Street NE" (Insomnia Cookies), or any address from another project. Wrong address = critical failure.

---

## 4. Date

- **Rule:** Always use **TODAY's date** in the proposal (e.g. MM-DD-YYYY and/or "February 15, 2026").
- **Never use:** A fixed or old date (e.g. 01-12-2026). Date must be dynamic at generation time.

---

## 5. Project Description – Exhibit A

- **Source:** The **"Project Information" / "Project Description"** text from the BuildingConnected **Overview** tab (or drawing cover page scope of work if BC Overview is incomplete). Use the **exact** project description for this project.
- **For St. Joseph's (exact from BC Overview):**  
  *"Renovation of an existing historic carriage house and addition of an event hall with a reception space. The event hall is one double height story of construction type V-B and the carriage house and reception area are two stories of construction type V-B. All spaces are sprinklered. Exterior improvements and new utilities are included in the scope of work."*
- **Never use:** A description from another project (e.g. tenant fit-out, 2 AHUs, shop space, restrooms, "Cox & Company"), or generic text not from the actual BC Overview / permit set. If you don't have the real description, do not invent it.

---

## 6. Scope of Work (SOW) – Client Party Name

- The SOW must state: *"...between Building Code Consulting, LLC ("BCC") and [Client Name from BC] ("Client")..."*.
- **For St. Joseph's:** Use **"Keller Brothers"** (or "Keller Brothers - Keller Brothers Special Projects") as the Client — **not** "Cox & Company, LLC" or any other name.
- **Rule:** When using an existing proposal as a template, **revise all client/attention/address/description** to match the current project. Never leave template client names in the document.

---

## 7. Discipline Applicability (Building, Mechanical, Electrical, Plumbing, Fire)

- **Rule:** Do **not** mark all disciplines "(applicable)" by default. Determine applicability by **reviewing the permit set and drawing index** (e.g. Bid Set Drawings). Check for: underground plumbing, TPF inspection, sprinkler tests, fire alarm tests, grease duct/Ansul, slab sleeve/conduit, shaft wall, duct fire damper, etc.
- Only mark a discipline as applicable if the project scope (from BC Overview description and/or drawing index) supports it. If not 100% sure, note "as applicable per permit set" or similar.

---

## 8. Estimated Fee – Exhibit C (PE/MCP Estimation Logic)

- **Do not use:** An old flat rate (e.g. $325/visit) or inspection types copied from a different project (e.g. small cookie shop). Do not use a table where "Total Visits" does not match the sum of visits in the rows.
- **Do:**
  1. **Scope triggers:** From project description and (when available) Bid Set Drawings / drawing index, identify: slab/concrete, underground plumbing or electrical, kitchen/grease duct/Ansul, fire protection upgrade, electrical service/TPF, etc.
  2. **Visit count:** Estimate number of inspections (underground, rough-in, close-in, finals, sprinkler/fire alarm tests, etc.) and ensure the **table rows sum correctly** to Total Visits.
  3. **Fee tier:**  
     - $295/visit: Extremely large or top-tier volume clients.  
     - $300–$350/visit: Regular large clients, standard mid-sized projects.  
     - $350–$375/visit: Small repeat clients.  
     - $375–$400/visit: One-time or highly complex, senior PE attention.
  4. **Total:** Total Fee = (Price Per Visit) × (Total Visits). Table totals must be consistent.
- **For St. Joseph's:** Carriage house + event hall, sprinklered, new utilities → Building, MEP, Fire applicable; underground and sprinkler tests likely. Example: ~20 visits at $350/visit = $7,000 (adjust rows to match).

---

## 9. Formatting and Color

- **Rule:** All body text in the final proposal must be **BLACK**. Red text indicates an unfinished placeholder. If any red remains, the proposal has failed verification.

---

## 10. Pre-Delivery: Gemini Double-Check (Optional but Recommended)

- Before sending the proposal to the user for final review, send a **summary** of the proposal (Client, Attention, Address, Date, Exhibit A text, Exhibit C fee/visits/total) to **Gemini** (API or web-based) and ask it to:
  - Confirm client name, address, and attention match the project.
  - Confirm date is today.
  - Confirm Exhibit A matches the project description for the named project.
  - Confirm Exhibit C visit count and fee logic are consistent and reasonable.
- If Gemini **approves**, present the proposal to the user for final review. If Gemini **rejects** or flags issues, fix and re-run the check (or report the issues and do not send until corrected).

---

## 11. Output Path

- Save to: `../Projects/[Real Client Name]/[Project Name]/`.  
- **For St. Joseph's:** Use client folder **"Keller Brothers"** (or "Keller Brothers - Keller Brothers Special Projects") and project folder **"St. Joseph's on Capitol Hill – Phase I"**, so path is e.g. `Projects/Keller Brothers/St. Joseph's on Capitol Hill – Phase I/`.

---

## Quick Checklist Before Sending Proposal to User

- [ ] Client name from BC Overview (not project name, not template).
- [ ] Attention/contact and email from BC (not Bryan Kerr or template).
- [ ] Address from BC Overview exact (not 701 Monroe).
- [ ] Date = today.
- [ ] Exhibit A = exact BC Project Description for this project (not another job).
- [ ] SOW client party = same as Client (not Cox & Company).
- [ ] Disciplines marked applicable only per permit set/drawing index.
- [ ] Exhibit C: PE/MCP logic, visits sum correct, no $325 cookie-shop copy.
- [ ] All text BLACK.
- [ ] Gemini double-check passed (if enabled).
