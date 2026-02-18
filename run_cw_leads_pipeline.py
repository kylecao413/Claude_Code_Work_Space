"""
run_cw_leads_pipeline.py — ConstructionWire Full DC Leads Pipeline (2026)

Phases:
  1. Scrape ALL DC leads (stages 1–12 months) with detail pages for all leads
  2. Deep-search each unique company for 2–3 POCs (name, role, email, phone)
  3. Compile comprehensive leads report → save Markdown
  4. Send leads report to Telegram
  5. Generate personalized cold-outreach emails per contact (BCC rules § 0-C / 0-E)
  6. Save email drafts to Pending_Approval/Outbound/CW_*.md
  7. Send email drafts to Telegram for Kyle's review

After review, run: python send_cw_outreach.py

Usage:
    python run_cw_leads_pipeline.py [--pages N] [--headless] [--max-contacts K]
    python run_cw_leads_pipeline.py --pages 5 --headless --max-contacts 3
    python run_cw_leads_pipeline.py --skip-research   # use only CW detail-page contacts
    python run_cw_leads_pipeline.py --skip-telegram   # no Telegram sending (local only)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import requests
from playwright.async_api import async_playwright

from constructionwire_login import COOKIES_PATH, has_saved_cookies, is_logged_in_url, LOGIN_URL
from constructionwire_dc_leads import (
    scrape_leads_from_current_page,
    scrape_detail_page,
    DC_SEARCH_URL,
    BASE_URL,
)
from deep_search_contacts import deep_search_contacts

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTBOUND_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
OUTBOUND_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_IDS_RAW = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
CHAT_ID = CHAT_IDS_RAW.split(",")[0].strip() if CHAT_IDS_RAW else ""

NOW_STR = datetime.now().strftime("%Y%m%d_%H%M")
TODAY = datetime.now().strftime("%Y-%m-%d")

# ─── Company role codes from ConstructionWire ─────────────────────────────────
# Ordered longest-first to avoid partial match (e.g. "(D/O)" before "(D)")
ROLE_PREFIXES: list[tuple[str, str]] = [
    ("(D/O)", "Developer/Owner"),
    ("(C/M)", "Construction Manager"),
    ("(CM)",  "Construction Manager"),
    ("(SE)",  "Structural Engineer"),
    ("(ME)",  "MEP Engineer"),
    ("(D)",   "Developer"),
    ("(O)",   "Owner"),
    ("(C)",   "GC/Contractor"),
    ("(A)",   "Architect"),
]


# ─── Telegram helpers ─────────────────────────────────────────────────────────
def tg_message(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("[TG] No bot token/chat ID — skipping.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chunk in [text[i : i + 4096] for i in range(0, len(text), 4096)]:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=15)
        if not r.ok:
            print(f"[TG] Message error: {r.status_code} {r.text[:200]}")
            return False
    return True


def tg_document(file_path: Path, caption: str = "") -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption[:1024]},
                files={"document": (file_path.name, f)},
                timeout=60,
            )
        if not r.ok:
            print(f"[TG] Document error: {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[TG] Document send failed: {e}")
        return False


# ─── Company parsing ──────────────────────────────────────────────────────────
def _parse_all_companies(companies_cell: str) -> list[tuple[str, str]]:
    """
    Parse the 'companies' cell from a CW list-page row.
    Returns list of (company_name, role) tuples.
    Role is human-readable: 'GC/Contractor', 'Developer', 'Owner', 'Architect', etc.
    ConstructionWire codes: (D/O), (D), (O), (C), (A), (C/M), (CM), (SE), (ME)
    """
    results: list[tuple[str, str]] = []
    for line in (companies_cell or "").splitlines():
        line = line.strip()
        if not line:
            continue
        matched = False
        for prefix, role in ROLE_PREFIXES:
            if line.startswith(prefix):
                company = line[len(prefix):].strip()
                if company:
                    results.append((company, role))
                matched = True
                break
        if not matched and line:
            # Unknown prefix — include as generic company
            results.append((line, "Company"))
    return results


def _first_name(full_name: str) -> str:
    """Extract first name from full name."""
    parts = (full_name or "").strip().split()
    return parts[0] if parts else ""


def _clean_company_name(name: str) -> str:
    """
    Strip CW navigation text appended to company names in detail pages.
    e.g. "Carr Properties\n\t\nWebsite\n•\nCompany Report" -> "Carr Properties"
    """
    if not name:
        return ""
    # Split on first newline or tab and take the first part
    cleaned = re.split(r"[\n\t]", name)[0].strip()
    return cleaned


# ─── Phase 1: Playwright scraping ─────────────────────────────────────────────
async def phase1_scrape_leads(headless: bool = False, max_pages: int = 10) -> list[dict]:
    """
    Scrape all DC leads (stages 1–12 months) with detail pages for every lead.
    Returns list of lead dicts with companies_parsed, detail_contacts, construction_start, etc.
    """
    if not has_saved_cookies():
        print("No saved CW cookies. Please run first: python constructionwire_login.py")
        return []

    print(f"\n{'='*60}")
    print("Phase 1: Scraping ConstructionWire DC Leads")
    print(f"{'='*60}")

    all_leads: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            storage_state=COOKIES_PATH,
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # Verify login via saved cookies
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=15000)
            if not is_logged_in_url(page.url):
                print("CW cookies expired. Please re-run: python constructionwire_login.py")
                return []
            print("Login via cookies: OK")

            # Scrape list pages
            for pagenum in range(1, max_pages + 1):
                url = DC_SEARCH_URL.replace("p=1", f"p={pagenum}")
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_load_state("networkidle", timeout=20000)
                try:
                    await page.wait_for_selector(
                        "#search-results-grid tr[data-report-id]", timeout=15000
                    )
                except Exception:
                    print(f"  Page {pagenum}: no results found — stopping pagination.")
                    break
                leads = await scrape_leads_from_current_page(page)
                if not leads:
                    print(f"  Page {pagenum}: 0 leads — stopping.")
                    break
                all_leads.extend(leads)
                print(f"  Page {pagenum}: {len(leads)} leads (total: {len(all_leads)})")

            if not all_leads:
                print("No leads found on any list page.")
                return []

            print(f"\nTotal list-page leads: {len(all_leads)}")

            # Scrape detail pages for ALL leads
            print("\nScraping detail pages for each lead...")
            for i, lead in enumerate(all_leads):
                detail_url = lead.get("detail_url", "")
                if not detail_url:
                    lead["detail_contacts"] = []
                    lead["companies_parsed"] = _parse_all_companies(lead.get("companies", ""))
                    continue
                print(f"  [{i+1}/{len(all_leads)}] {(lead.get('project_name','') or '')[:55]}...")
                try:
                    extra = await scrape_detail_page(page, detail_url)
                    lead["detail"] = extra
                    if extra.get("stage"):
                        lead["stage"] = extra["stage"]
                    if extra.get("construction_start"):
                        lead["construction_start"] = extra["construction_start"]
                    if extra.get("construction_end"):
                        lead["construction_end"] = extra["construction_end"]
                    lead["detail_contacts"] = extra.get("contacts", [])
                except Exception as e:
                    print(f"    Detail error: {e}")
                    lead["detail"] = {}
                    lead["detail_contacts"] = []
                finally:
                    lead["companies_parsed"] = _parse_all_companies(lead.get("companies", ""))

        finally:
            await browser.close()

    print(f"\nPhase 1 complete: {len(all_leads)} leads scraped with details.")
    return all_leads


# ─── Phase 2: Deep search + phone ─────────────────────────────────────────────
def _search_phone(contact_name: str, company: str) -> str:
    """Try to find a phone number for a contact via DuckDuckGo/ddgs. Returns first match or ''."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return ""
    if not contact_name or not company:
        return ""
    phone_re = re.compile(r"\b(?:\+1[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?)?\d{3}[\s.\-]?\d{4}\b")
    try:
        with DDGS() as ddgs:
            for q in [f'"{contact_name}" {company} phone', f'"{contact_name}" {company} contact number']:
                for r in ddgs.text(q, max_results=5):
                    body = (r.get("body") or "") + " " + (r.get("title") or "")
                    phones = [m for m in phone_re.findall(body) if len(re.sub(r"\D", "", m)) >= 10]
                    if phones:
                        return phones[0]
    except Exception:
        pass
    return ""


def phase2_research_companies(
    leads: list[dict], max_contacts: int = 3
) -> dict[str, dict]:
    """
    Deep-search every unique company found across all leads.
    Returns: company_name -> {role, contacts: [{name, role, email, phone, source}]}
    Priority: ConstructionWire detail-page contacts (verified) then deep search supplements.
    """
    print(f"\n{'='*60}")
    print("Phase 2: Deep-Searching Companies for Key Contacts")
    print(f"{'='*60}")

    # Build unique company → role map (prefer more specific roles)
    role_priority = {
        "Developer/Owner": 0, "Developer": 1, "Owner": 2,
        "GC/Contractor": 3, "Construction Manager": 4,
        "Architect": 5, "Structural Engineer": 6, "MEP Engineer": 7, "Company": 99,
    }
    company_role_map: dict[str, str] = {}
    for lead in leads:
        for (company, role) in lead.get("companies_parsed", []):
            if company:
                existing = company_role_map.get(company)
                if existing is None or role_priority.get(role, 99) < role_priority.get(existing, 99):
                    company_role_map[company] = role
        for dc in lead.get("detail_contacts", []):
            # Clean company name — detail pages append navigation text after newline/tab
            comp = _clean_company_name(dc.get("company") or "")
            role = (dc.get("role") or "Company").strip()
            if comp and comp not in company_role_map:
                company_role_map[comp] = role

    print(f"Unique companies to research: {len(company_role_map)}")

    results: dict[str, dict] = {}
    for idx, (company, role) in enumerate(company_role_map.items()):
        print(f"\n  [{idx+1}/{len(company_role_map)}] {company} ({role})")

        # Step A: collect verified contacts from CW detail pages
        cw_contacts: list[dict] = []
        seen_emails: set[str] = set()
        for lead in leads:
            for dc in lead.get("detail_contacts", []):
                # Compare using cleaned company name to handle navigation text
                if _clean_company_name(dc.get("company") or "").lower() != company.lower():
                    continue
                name = (dc.get("name") or dc.get("contact", "").split("\n")[0]).strip()
                email = (dc.get("email") or "").strip()
                if email and email in seen_emails:
                    continue
                if email:
                    seen_emails.add(email)
                cw_contacts.append({
                    "name": name,
                    "role": (dc.get("role") or "").strip(),
                    "email": email,
                    "phone": "",
                    "source": "ConstructionWire detail page",
                })

        # Step B: deep search to supplement
        ds_contacts = deep_search_contacts(company, max_contacts=max_contacts, use_gemini=True)
        for c in ds_contacts:
            e = (c.get("email") or "").strip()
            if e and e in seen_emails:
                continue
            if e:
                seen_emails.add(e)
            cw_contacts.append({
                "name": (c.get("name") or "").strip(),
                "role": (c.get("role") or "").strip(),
                "email": e,
                "phone": "",
                "source": c.get("source", "deep search"),
            })

        # Keep only max_contacts, prioritize those with emails
        cw_contacts.sort(key=lambda c: (0 if c["email"] else 1))
        final_contacts = cw_contacts[:max_contacts]

        # Step C: phone lookup for contacts that have a name + email
        for c in final_contacts[:3]:
            if not c["phone"] and c.get("name") and c.get("email"):
                phone = _search_phone(c["name"], company)
                if phone:
                    c["phone"] = phone
                    print(f"    Phone found for {c['name']}: {phone}")

        results[company] = {"role": role, "contacts": final_contacts}
        found = sum(1 for c in final_contacts if c.get("email"))
        print(f"    Contacts with email: {found} / {len(final_contacts)}")

    print(f"\nPhase 2 complete: {len(results)} companies researched.")
    return results


# ─── Phase 3: Compile report ───────────────────────────────────────────────────
def phase3_compile_report(leads: list[dict], company_research: dict[str, dict]) -> str:
    """
    Compile a Markdown leads + contacts report.
    Columns: Project, Stage, Est. Value, Start Date, Company, Role, Contact, Email, Phone
    """
    print(f"\n{'='*60}")
    print("Phase 3: Compiling Leads Report")
    print(f"{'='*60}")

    lines = [
        "# BCC DC Construction Leads Report",
        f"_Generated: {TODAY} | Source: ConstructionWire DC | Stages: 1–12 months_\n",
        f"**Total leads scraped:** {len(leads)}\n",
        "---\n",
        "## Leads Summary\n",
        "| # | Project | Stage | Est. Value | Start Date | Companies |",
        "|---|---------|-------|------------|------------|-----------|",
    ]
    for i, lead in enumerate(leads, 1):
        project = (lead.get("project_name") or "").strip()[:52]
        stage = (lead.get("stage") or "").strip()[:30]
        value = (lead.get("estimated_value") or "").strip()[:15]
        start = (lead.get("construction_start") or lead.get("schedule") or "").strip()[:20]
        companies_str = "; ".join(
            f"{r}: {c}" for c, r in lead.get("companies_parsed", [])
        )[:65]
        lines.append(f"| {i} | {project} | {stage} | {value} | {start} | {companies_str} |")

    lines += ["\n---\n", "## Detailed Contacts per Project\n"]

    for i, lead in enumerate(leads, 1):
        project = (lead.get("project_name") or "N/A").strip()
        addr = ", ".join(
            filter(None, [lead.get("address"), lead.get("city"), lead.get("state")])
        )
        stage = (lead.get("stage") or "").strip()
        value = (lead.get("estimated_value") or "").strip()
        start = (lead.get("construction_start") or lead.get("schedule") or "TBD").strip()
        url = lead.get("detail_url", "")

        lines.append(f"### {i}. {project}")
        if addr:
            lines.append(f"- **Address:** {addr}")
        lines.append(f"- **Stage:** {stage}")
        lines.append(f"- **Est. Value:** {value}")
        lines.append(f"- **Construction Start:** {start}")
        if url:
            lines.append(f"- **CW Link:** {url}")
        lines.append("")

        companies_parsed = lead.get("companies_parsed", [])
        if not companies_parsed:
            lines.append("_No companies parsed._\n")
            continue

        lines.append("| Company | Role | Contact | Email | Phone |")
        lines.append("|---------|------|---------|-------|-------|")
        for (company, role) in companies_parsed:
            contacts = company_research.get(company, {}).get("contacts", [])
            if not contacts:
                lines.append(f"| {company} | {role} | — | — | — |")
            else:
                for c in contacts:
                    name = (c.get("name") or "").strip() or "—"
                    email = (c.get("email") or "").strip() or "—"
                    phone = (c.get("phone") or "").strip() or "—"
                    crow = (c.get("role") or role).strip() or role
                    lines.append(f"| {company} | {crow} | {name} | {email} | {phone} |")
        lines.append("")

    print("Phase 3 complete.")
    return "\n".join(lines)


# ─── Phase 4: Send report to Telegram ─────────────────────────────────────────
def phase4_send_report_telegram(report_md: str, report_path: Path) -> None:
    print(f"\n{'='*60}")
    print("Phase 4: Sending Leads Report to Telegram")
    print(f"{'='*60}")

    summary_end = report_md.find("## Detailed Contacts per Project")
    summary = report_md[:summary_end] if summary_end > 0 else report_md[:3500]

    tg_message(
        f"📊 *BCC DC Leads Report — {TODAY}*\n"
        f"Source: ConstructionWire | Stages 1–12 months\n\n"
        f"Full report attached. Summary preview:\n\n{summary[:3200]}"
    )
    tg_document(report_path, caption=f"DC_Leads_Report_{TODAY}.md")
    print("Report sent to Telegram.")


# ─── Phase 5: Generate cold outreach emails ────────────────────────────────────
def _map_cw_role(raw_role: str) -> str:
    """
    Map CW detail-page role strings (e.g. 'General Contractor', 'Bidding General Contractor',
    'Developer, Owner', 'Tenant') to our canonical role categories for email body selection.
    """
    r = (raw_role or "").lower()
    if any(k in r for k in ("general contractor", "bidding", "construction manager", "cm")):
        return "GC/Contractor"
    if any(k in r for k in ("developer", "owner")):
        return "Developer/Owner"
    if "architect" in r:
        return "Architect"
    return raw_role  # pass through for default handling


def _role_is_gc_or_cm(role: str) -> bool:
    return any(r in role for r in ("GC", "Contractor", "Construction Manager", "CM"))


def _role_is_developer_or_owner(role: str) -> bool:
    return any(r in role for r in ("Developer", "Owner"))


def _role_is_architect(role: str) -> bool:
    return "Architect" in role


def _generate_email_body(
    contact_name: str, company: str, role: str, project_name: str
) -> str:
    """
    Generate cold outreach email body per BCC rules § 0-C / § 0-E:
    - GC/CM targets: DC Inspections ONLY — no plan review mention
    - Developer/Owner: include plan review note
    - Architect: include peer review + inspection
    - No signature (admin@ auto-signature handles it)
    - No ellipses
    - Always include billing disclaimer in the billing bullet
    """
    first = _first_name(contact_name)
    salutation = f"Hi {first}," if first else "Hi,"

    bullet_expertise = (
        "Multi-Discipline Expertise: Our team holds PE licenses (Civil and Electrical) and ICC "
        "Master Code Professional (MCP) certifications. We handle Building, Mechanical, "
        "Electrical, Plumbing, and Fire inspections under one roof and resolve technical code "
        "questions on-site to prevent delays."
    )
    bullet_scheduling = (
        "Responsive Scheduling: We offer same-day or next-business-day inspection availability "
        "to keep your project milestones on track."
    )
    bullet_billing = (
        "Fair, Visit-Based Billing: Billing is based on actual visits completed — our fee is a "
        "flat rate per inspection visit actually performed. You will never be billed based on an "
        "upfront estimate. If your project wraps up in fewer inspections than projected, you pay "
        "only for what was done."
    )

    if _role_is_gc_or_cm(role):
        # GC / Construction Manager: inspection pitch only, DC-specific
        parts = [
            salutation,
            "",
            f"I noticed {company} is working on {project_name} in Washington, DC and wanted "
            f"to take a moment to introduce Building Code Consulting LLC (BCC) as a potential "
            f"resource for your Third-Party Inspection needs.",
            "",
            f"BCC is a DC-based engineering firm focused exclusively on Washington, D.C. "
            f"Third-Party Code Compliance Inspections. A few reasons {company} may find us "
            f"a strong fit for this project:",
            "",
            bullet_expertise,
            "",
            bullet_scheduling,
            "",
            bullet_billing,
            "",
            "We are not submitting a formal proposal at this stage, but if you are still "
            "finalizing your inspection vendor list for this project, we would welcome the "
            "opportunity to provide a competitive quote.",
            "",
            "Are you open to a quick 5-minute call or a brief capability overview?",
        ]

    elif _role_is_developer_or_owner(role):
        # Developer / Owner: inspection + plan review note
        parts = [
            salutation,
            "",
            f"I came across {project_name} and wanted to briefly introduce Building Code "
            f"Consulting LLC (BCC) as a resource for {company}'s Third-Party Inspection "
            f"and Plan Review needs.",
            "",
            f"BCC is a DC-based firm specializing in Third-Party Code Compliance Inspections "
            f"and Plan Review. A few highlights:",
            "",
            bullet_expertise,
            "",
            bullet_scheduling,
            "",
            bullet_billing,
            "",
            "Also, as a quick note — BCC also offers Third-Party Plan Review Services for DC "
            "and nationwide jurisdictions. If your team needs expedited pre-submission code "
            "review or peer review, we would be glad to assist.",
            "",
            f"We are not submitting a formal proposal at this stage, but if you would like to "
            f"learn more about our services for {project_name}, we would welcome the conversation.",
            "",
            "Are you open to a quick 5-minute call?",
        ]

    elif _role_is_architect(role):
        # Architect: peer review + inspection, technical framing
        parts = [
            salutation,
            "",
            f"I came across {project_name} and wanted to briefly introduce Building Code "
            f"Consulting LLC (BCC). We often collaborate with architects on Third-Party Code "
            f"Compliance reviews and inspections for DC projects.",
            "",
            f"BCC is a DC-based firm specializing in DC Third-Party Code Compliance and Plan "
            f"Review. A few highlights relevant to {company}:",
            "",
            bullet_expertise,
            "",
            bullet_scheduling,
            "",
            bullet_billing,
            "",
            "We also offer Third-Party Plan Review and peer review services that can help "
            "identify code issues before submission — reducing revision cycles and protecting "
            "your project schedule.",
            "",
            f"We are not submitting a formal proposal at this stage, but would welcome the "
            f"opportunity to discuss how BCC can support {project_name}.",
            "",
            "Are you open to a quick 5-minute call?",
        ]

    else:
        # Default: conservative inspection-only pitch
        parts = [
            salutation,
            "",
            f"I came across {project_name} and wanted to briefly introduce Building Code "
            f"Consulting LLC (BCC) as a potential resource for Third-Party Inspection needs.",
            "",
            "BCC is a DC-based engineering firm specializing in Washington, D.C. Third-Party "
            "Code Compliance Inspections. A few reasons we may be a strong fit:",
            "",
            bullet_expertise,
            "",
            bullet_scheduling,
            "",
            bullet_billing,
            "",
            "We are not submitting a formal proposal at this stage, but if you are exploring "
            "inspection vendors for this project, we would welcome a brief conversation.",
            "",
            "Are you open to a quick 5-minute call?",
        ]

    return "\n".join(parts)


def phase5_generate_emails(
    leads: list[dict], company_research: dict[str, dict]
) -> list[dict]:
    """
    Generate one cold outreach email per (project, company, contact).
    Subject: "Third-Party Inspection Services for [Project] | Building Code Consulting LLC"
    No "bid inquiry", no "Proposal" language, no signature.
    Returns list of email dicts.
    """
    print(f"\n{'='*60}")
    print("Phase 5: Generating Cold Outreach Emails")
    print(f"{'='*60}")

    emails: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (email_lower, project)

    def _add_email(project_name: str, company: str, role: str,
                   contact_name: str, contact_role: str, email_addr: str, phone: str) -> None:
        key = (email_addr.lower(), project_name)
        if key in seen:
            return
        seen.add(key)
        subject = (
            f"Third-Party Inspection Services for {project_name} | Building Code Consulting LLC"
        )
        body = _generate_email_body(contact_name, company, role, project_name)
        safe_slug = re.sub(r"[^\w]", "_", f"{company}_{contact_name or 'Contact'}")[:48]
        safe_slug = re.sub(r"_+", "_", safe_slug).strip("_")
        emails.append({
            "slug": safe_slug,
            "project": project_name,
            "company": company,
            "company_role": role,
            "contact_role": contact_role,
            "contact_name": contact_name,
            "to_email": email_addr,
            "phone": phone,
            "subject": subject,
            "body": body,
        })

    for lead in leads:
        project_name = (lead.get("project_name") or "").strip()
        if not project_name:
            continue

        # ── Source 1: CW detail-page contacts (highest quality — verified emails) ──
        for dc in lead.get("detail_contacts", []):
            email_addr = (dc.get("email") or "").strip()
            if not email_addr or "@" not in email_addr:
                continue
            company = _clean_company_name(dc.get("company") or "")
            if not company:
                continue
            contact_name = (dc.get("name") or "").strip()
            role = (dc.get("role") or "").strip()
            # Map CW role strings to our role categories for email body selection
            role_mapped = _map_cw_role(role)
            _add_email(project_name, company, role_mapped, contact_name, role, email_addr, "")

        # ── Source 2: Deep-search contacts for companies in companies_parsed ──
        for (company, role) in lead.get("companies_parsed", []):
            research = company_research.get(company, {})
            for contact in research.get("contacts", []):
                email_addr = (contact.get("email") or "").strip()
                if not email_addr:
                    continue
                contact_name = (contact.get("name") or "").strip()
                contact_role = (contact.get("role") or role).strip()
                phone = (contact.get("phone") or "").strip()
                _add_email(project_name, company, role, contact_name, contact_role, email_addr, phone)

    print(f"Phase 5 complete: {len(emails)} email drafts generated.")
    return emails


# ─── Phase 6: Save drafts ──────────────────────────────────────────────────────
def phase6_save_drafts(email_drafts: list[dict]) -> list[Path]:
    """
    Save each email as CW_[slug]_[TIMESTAMP].md in Pending_Approval/Outbound/.
    Cleans up old CW_*.md drafts first.
    """
    print(f"\n{'='*60}")
    print("Phase 6: Saving Email Drafts")
    print(f"{'='*60}")

    # Clean up previous CW pipeline drafts
    for old in OUTBOUND_DIR.glob("CW_*.md"):
        old.unlink()
        print(f"  Deleted old draft: {old.name}")

    saved: list[Path] = []
    for em in email_drafts:
        fname = f"CW_{em['slug']}_{NOW_STR}.md"
        fpath = OUTBOUND_DIR / fname
        content = (
            f"# CW Cold Outreach — {em['company']}\n"
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"**PROJECT:** {em['project']}\n"
            f"**TO:** {em['contact_name']} <{em['to_email']}>\n"
            f"**PHONE:** {em['phone'] or '—'}\n"
            f"**CC:** ycao@buildingcodeconsulting.com (auto)\n"
            f"**FROM:** admin@buildingcodeconsulting.com\n"
            f"**COMPANY ROLE:** {em['company_role']}\n"
            f"**SUBJECT:** {em['subject']}\n\n"
            f"---\n\n"
            f"{em['body']}\n"
        )
        fpath.write_text(content, encoding="utf-8")
        saved.append(fpath)
        print(f"  Saved: {fname}")

    print(f"Phase 6 complete: {len(saved)} drafts saved to Pending_Approval/Outbound/")
    return saved


# ─── Phase 7: Send drafts to Telegram ─────────────────────────────────────────
def phase7_send_drafts_telegram(email_drafts: list[dict], saved_paths: list[Path]) -> None:
    """Send summary + each draft file to Telegram for Kyle's review."""
    print(f"\n{'='*60}")
    print("Phase 7: Sending Email Drafts to Telegram")
    print(f"{'='*60}")

    # Group by company to give a clean overview
    by_company: dict[str, list[dict]] = {}
    for em in email_drafts:
        by_company.setdefault(em["company"], []).append(em)

    tg_message(
        f"📧 *BCC CW Cold Outreach Drafts — {TODAY}*\n\n"
        f"Total drafts: {len(email_drafts)}\n"
        f"Companies: {len(by_company)}\n\n"
        f"All drafts saved locally to Pending_Approval/Outbound/CW_*.md\n"
        f"These are cold outreach emails — NO PDF attached.\n\n"
        f"After review, run: `python send_cw_outreach.py`"
    )

    # Send each draft as text preview + file
    for em, fpath in zip(email_drafts, saved_paths):
        preview = (
            f"📨 *{em['company']}* ({em['company_role']})\n"
            f"Project: {em['project']}\n"
            f"To: {em['contact_name']} <{em['to_email']}>"
            + (f"\nPhone: {em['phone']}" if em["phone"] else "")
            + f"\nSubject: {em['subject']}\n\n---\n{em['body'][:700]}"
        )
        tg_message(preview)

    tg_message(
        "✅ All drafts sent above.\n"
        "Review and reply with approval, then run: python send_cw_outreach.py"
    )
    print(f"Phase 7 complete: {len(email_drafts)} drafts sent to Telegram.")


# ─── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(
        description="ConstructionWire Full DC Leads Pipeline — scrape, research, generate emails"
    )
    ap.add_argument("--pages", type=int, default=5, help="Max list pages to scrape (default: 5)")
    ap.add_argument("--headless", action="store_true", help="Run Playwright browser headless")
    ap.add_argument("--max-contacts", type=int, default=3, help="Max contacts per company (default: 3)")
    ap.add_argument("--skip-research", action="store_true", help="Use only CW detail-page contacts (no deep search)")
    ap.add_argument("--skip-telegram", action="store_true", help="Skip all Telegram sends (local output only)")
    args = ap.parse_args()

    # ── Phase 1: Scrape ──────────────────────────────────────────────────────
    leads = asyncio.run(phase1_scrape_leads(headless=args.headless, max_pages=args.pages))
    if not leads:
        print("No leads found. Exiting.")
        return 1

    # Save raw JSON for debugging / resume
    raw_path = BASE_DIR / f"cw_leads_raw_{NOW_STR}.json"
    raw_path.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Raw leads JSON: {raw_path.name}")

    # ── Phase 2: Research ────────────────────────────────────────────────────
    if args.skip_research:
        print("\n[--skip-research] Using CW detail-page contacts only.")
        company_research: dict[str, dict] = {}
        for lead in leads:
            for (company, role) in lead.get("companies_parsed", []):
                if company not in company_research:
                    company_research[company] = {"role": role, "contacts": []}
            for dc in lead.get("detail_contacts", []):
                comp = (dc.get("company") or "").strip()
                if not comp:
                    continue
                if comp not in company_research:
                    company_research[comp] = {"role": dc.get("role", ""), "contacts": []}
                company_research[comp]["contacts"].append({
                    "name": (dc.get("name") or dc.get("contact", "").split("\n")[0]).strip(),
                    "role": (dc.get("role") or "").strip(),
                    "email": (dc.get("email") or "").strip(),
                    "phone": "",
                    "source": "CW detail page",
                })
    else:
        company_research = phase2_research_companies(leads, max_contacts=args.max_contacts)

    # ── Phase 3: Report ──────────────────────────────────────────────────────
    report_md = phase3_compile_report(leads, company_research)
    report_path = BASE_DIR / f"DC_Leads_Report_{NOW_STR}.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\nReport saved: {report_path.name}")

    # Also print summary to terminal for Kyle to review now
    summary_end = report_md.find("## Detailed Contacts per Project")
    print("\n" + ("=" * 60))
    print(report_md[:summary_end] if summary_end > 0 else report_md[:2000])

    # ── Phase 4: Telegram report ─────────────────────────────────────────────
    if not args.skip_telegram:
        phase4_send_report_telegram(report_md, report_path)

    # ── Phase 5: Generate emails ─────────────────────────────────────────────
    email_drafts = phase5_generate_emails(leads, company_research)
    if not email_drafts:
        print("\nNo email drafts generated (no contacts with emails found).")
        print("Tip: Run without --skip-research or check that CW detail pages have contacts.")
        return 0

    # ── Phase 6: Save drafts ─────────────────────────────────────────────────
    saved_paths = phase6_save_drafts(email_drafts)

    # ── Phase 7: Telegram drafts ─────────────────────────────────────────────
    if not args.skip_telegram:
        phase7_send_drafts_telegram(email_drafts, saved_paths)

    print(f"\n{'='*60}")
    print("Pipeline COMPLETE")
    print(f"  Leads scraped:        {len(leads)}")
    print(f"  Companies researched: {len(company_research)}")
    print(f"  Email drafts:         {len(email_drafts)}")
    print(f"  Report:               {report_path.name}")
    print(f"  Drafts:               Pending_Approval/Outbound/CW_*.md")
    print(f"\nNext step — after reviewing drafts on Telegram:")
    print(f"  python send_cw_outreach.py")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
