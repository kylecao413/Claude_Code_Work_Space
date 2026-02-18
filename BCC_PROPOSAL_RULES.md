# BCC Proposal Generation – Mandatory Rules (No Exceptions)

These rules are derived from the Critical Failure Report and screenshot corrections. **Every proposal must follow them.**

---

## 0. Scraping / BuildingConnected – Correct Methods (Must Be Updated When Found)

**Protocol:** When the agent (or you and the agent together) **finds the correct way** to get a specific data point from BuildingConnected (e.g. Project Description, Client, Address, Contact)—by identifying the right CSS selector, XPath, or step-by-step flow—**do not just fix the code and move on.**

1. **Immediately** open this file (`BCC_PROPOSAL_RULES.md`).
2. Find the section below that corresponds to that data point (or create a subsection under "Scraping – Recorded methods").
3. **Delete** the old, incorrect rule or selector.
4. **Replace** it with a clear, step-by-step description of the **new, correct** method (selector, container, optional fallbacks).
5. Tell the agent: *"Future attempts to scrape this site MUST follow the rule stored in this markdown file."*

**Scraping – Recorded methods (overwrite when you find a better one):**

- **Project Description / Exhibit A:** *(To be filled when correct BC Overview selector or extraction steps are confirmed. Delete this line and write the exact method.)*
- **Client name:** *(To be filled when correct BC Overview field/selector is confirmed.)*
- **Address / Location:** *(To be filled when correct BC Overview field/selector is confirmed.)*
- **Attention / Contact (To:):** *(To be filled when correct BC Bid Form or Overview selector is confirmed.)*

If a scrape fails or returns wrong data, investigate the live HTML with the user, find the correct method once, then **update this section** so the same mistake is not repeated.

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
