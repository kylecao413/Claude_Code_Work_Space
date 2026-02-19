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
    BASE_URL,
)
from deep_search_contacts import deep_search_contacts

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTBOUND_DIR = BASE_DIR / "Pending_Approval" / "Outbound"
OUTBOUND_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_PATH = BASE_DIR / "pipeline_checkpoint.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_IDS_RAW = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
CHAT_ID = CHAT_IDS_RAW.split(",")[0].strip() if CHAT_IDS_RAW else ""

NOW_STR = datetime.now().strftime("%Y%m%d_%H%M")
TODAY = datetime.now().strftime("%Y-%m-%d")

# ─── Checkpoint utilities ─────────────────────────────────────────────────────

def _checkpoint_load() -> dict:
    """Load pipeline checkpoint. Returns {} if none exists or is corrupt."""
    if not CHECKPOINT_PATH.exists():
        return {}
    try:
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _checkpoint_save(updates: dict) -> None:
    """Merge updates into the checkpoint file atomically."""
    cp = _checkpoint_load()
    cp.update(updates)
    cp["last_updated"] = datetime.now().isoformat()
    CHECKPOINT_PATH.write_text(json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8")


def _checkpoint_clear() -> None:
    """Remove checkpoint file after successful pipeline completion."""
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        print("Checkpoint cleared (pipeline complete).")


def _checkpoint_resume_phase(cp: dict) -> int:
    """
    Return the phase number to resume from (1–7).
    Inspects which phases are marked done and returns the first incomplete one.
    """
    for phase, key in [
        (1, "phase1_done"), (2, "phase2_done"), (3, "phase3_done"),
        (4, "phase4_done"), (5, "phase5_done"), (6, "phase6_done"), (7, "phase7_done"),
    ]:
        if not cp.get(key):
            return phase
    return 8  # all done


# ─── Stage codes & service focus ─────────────────────────────────────────────
# CW pcstgs codes (confirmed by inspection of search URL params):
#   1 = Planning   2 = Proposed   3 = Starts 1-3 mo   4 = Starts 4-12 mo
#   5 = Starts 7-12 mo (some accounts combine 4+5)   6 = Groundbreaking   7 = Under Construction
DEFAULT_STAGES = [1, 2, 3, 4, 5, 6, 7]


def _build_search_url(stages: list[int]) -> str:
    params = "&".join(f"pcstgs={s}" for s in stages)
    return f"{BASE_URL}/Client/Report?rtid=1&rss=DC&{params}&p=1"


def _stage_service_focus(stage_text: str) -> tuple[str, int]:
    """
    Map scraped stage label → (service_focus, priority_score 1-10).
    Earlier stages → Plan Review priority. Later stages → Inspection priority.
    """
    s = (stage_text or "").lower()
    if any(x in s for x in ("planning", "proposed", "pre-design", "design development")):
        return "Plan Review", 9
    elif any(x in s for x in ("1-3", "1 to 3", "starts in 1", "1–3")):
        return "Both (Inspection Lead)", 10
    elif any(x in s for x in ("4-6", "4 to 6", "4–6", "4-12", "4 to 12", "7-12", "7 to 12", "7–12")):
        return "Inspection", 8
    elif any(x in s for x in ("groundbreaking", "breaking ground")):
        return "Inspection (Imminent)", 9
    elif any(x in s for x in ("under construction", "early construction", "construction")):
        return "Inspection (Active)", 7
    else:
        return "Both", 6


def _parse_value_millions(value_str: str) -> float:
    """Parse estimated value string → float in millions. Returns 0.0 on failure."""
    if not value_str:
        return 0.0
    s = value_str.lower().replace(",", "").replace("$", "").strip()
    m = re.search(r"[\d.]+", s)
    if not m:
        return 0.0
    try:
        num = float(m.group())
    except ValueError:
        return 0.0
    if "billion" in s or "b" == s[-1:]:
        return num * 1000
    if "million" in s or s.endswith("m"):
        return num
    # Raw number — assume dollars
    return num / 1_000_000


def _score_lead(lead: dict, company_research: dict) -> float:
    """Score a lead for top-100 ranking. Higher = better opportunity for BCC."""
    _, stage_score = _stage_service_focus(lead.get("stage", ""))
    score = float(stage_score)

    # Value: up to +5 for large projects (capped at $50M+)
    value_m = _parse_value_millions(lead.get("estimated_value") or lead.get("value") or "")
    score += min(value_m / 10.0, 5.0)

    # Contact quality: +3 if any CW detail contact has a verified email
    has_email = any(dc.get("email") for dc in lead.get("detail_contacts", []))
    if has_email:
        score += 3.0

    # Role desirability
    for (_, role) in lead.get("companies_parsed", []):
        if role in ("Developer/Owner", "Developer", "Owner"):
            score += 2.0
            break
        elif role in ("GC/Contractor", "Architect", "Construction Manager"):
            score += 1.0
            break

    return round(score, 2)


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
async def phase1_scrape_leads(
    headless: bool = False, max_pages: int = 10, stages: list[int] | None = None
) -> list[dict]:
    """
    Scrape DC leads for the given stage codes with detail pages for every lead.
    stages: list of CW pcstgs codes (1=Planning,2=Proposed,3-5=1-12mo,6=Groundbreaking,7=Early Construction)
    Returns list of lead dicts with companies_parsed, detail_contacts, construction_start, etc.
    """
    if stages is None:
        stages = DEFAULT_STAGES
    search_url = _build_search_url(stages)
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

            print(f"Stages: {stages} | URL: {search_url}")
            # Scrape list pages
            for pagenum in range(1, max_pages + 1):
                url = search_url.replace("p=1", f"p={pagenum}")
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
    leads: list[dict],
    max_contacts: int = 3,
    existing_research: dict | None = None,
    skip_companies: set | None = None,
) -> dict[str, dict]:
    """
    Deep-search every unique company found across all leads.
    Returns: company_name -> {role, contacts: [{name, role, email, phone, source}]}
    Priority: ConstructionWire detail-page contacts (verified) then deep search supplements.

    existing_research: partial results from a previous interrupted run (checkpoint resume).
    skip_companies: set of company names already fully researched (skip them).
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

    # Start from existing partial results (checkpoint resume)
    results: dict[str, dict] = dict(existing_research) if existing_research else {}
    _skip = set(skip_companies) if skip_companies else set()
    if _skip:
        print(f"  [RESUME] Skipping {len(_skip)} already-researched companies.")

    for idx, (company, role) in enumerate(company_role_map.items()):
        if company in _skip:
            continue
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
        _skip.add(company)
        found = sum(1 for c in final_contacts if c.get("email"))
        print(f"    Contacts with email: {found} / {len(final_contacts)}")
        # Incremental checkpoint save so a crash mid-phase is recoverable
        _checkpoint_save({
            "phase2_company_research": results,
            "phase2_researched": list(_skip),
        })

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


# ─── Phase 3b: Rank Top 100 Leads ─────────────────────────────────────────────
def phase_rank_top100(leads: list[dict], company_research: dict[str, dict]) -> str:
    """
    Score and rank all scraped leads. Return a Markdown report of the top 100.
    Columns: Rank, Project, Stage, Service Focus, Est. Value, Company/Role, Contact, Email
    Earlier stages → Plan Review emphasis. Later stages → Inspection emphasis.
    """
    print(f"\n{'='*60}")
    print("Phase 3b: Ranking Top 100 Leads")
    print(f"{'='*60}")

    scored = []
    for lead in leads:
        score = _score_lead(lead, company_research)
        service_focus, _ = _stage_service_focus(lead.get("stage") or "")
        # Best contact from detail page (prefer email-verified)
        best_contact = next(
            (dc for dc in lead.get("detail_contacts", []) if dc.get("email")),
            (lead.get("detail_contacts") or [{}])[0] if lead.get("detail_contacts") else {}
        )
        contact_name = _clean_company_name(best_contact.get("name") or best_contact.get("contact") or "")
        contact_email = best_contact.get("email") or ""
        contact_company = _clean_company_name(best_contact.get("company") or "")
        contact_role = best_contact.get("role") or ""

        # Fall back to companies_parsed if no detail contact
        if not contact_company and lead.get("companies_parsed"):
            contact_company, contact_role = lead["companies_parsed"][0]

        scored.append({
            "lead": lead,
            "score": score,
            "service_focus": service_focus,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_company": contact_company,
            "contact_role": contact_role,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top100 = scored[:100]

    lines = [
        "# BCC DC Leads — Top 100 Prioritized List",
        f"_Generated: {TODAY} | Scored by: stage priority + project value + contact quality_\n",
        "**Scoring guide:** Earlier stage = Plan Review focus | Later stage = Inspection focus\n",
        "---\n",
        "| # | Project | Stage | Focus | Est. Value | Company | Role | Contact | Email | Score |",
        "|---|---------|-------|-------|------------|---------|------|---------|-------|-------|",
    ]

    for i, item in enumerate(top100, 1):
        lead = item["lead"]
        project = (lead.get("project_name") or "").strip()[:45]
        stage = (lead.get("stage") or "").strip()[:25]
        focus = item["service_focus"][:20]
        value = (lead.get("estimated_value") or lead.get("value") or "—").strip()[:12]
        company = item["contact_company"][:30]
        role = item["contact_role"][:20]
        contact = item["contact_name"][:20]
        email = item["contact_email"][:35]
        score = item["score"]
        lines.append(f"| {i} | {project} | {stage} | {focus} | {value} | {company} | {role} | {contact} | {email} | {score} |")

    report = "\n".join(lines)
    print(f"Top 100 ranking complete. Top lead: {top100[0]['lead'].get('project_name', '')} (score {top100[0]['score']})")
    return report


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
    contact_name: str, company: str, role: str, project_name: str,
    service_focus: str = "Inspection",
) -> str:
    """
    Generate cold outreach email body per BCC rules § 0-C / § 0-E / § 0-G / § 0-H.
    - GC/CM: Inspection ONLY — no plan review mention (regardless of stage)
    - Developer/Owner / Architect: stage-aware pitch
      - service_focus "Plan Review" → lead with Plan Review, mention inspections as follow-on
      - otherwise → lead with Inspections, note plan review as add-on
    - No signature, no ellipses, correct PE credentials (Civil and Electrical)
    """
    first = _first_name(contact_name)
    salutation = f"Hi {first}," if first else "Hi,"
    is_plan_review_focus = "Plan Review" in service_focus and not _role_is_gc_or_cm(role)

    bullet_expertise = (
        "Multi-Discipline Expertise: Our team brings together licensed Professional Engineers "
        "across all major disciplines and multiple ICC Master Code Professionals (MCP). We handle "
        "Building, Mechanical, Electrical, Plumbing, and Fire Protection code inspections and plan "
        "review — and serve as a hands-on technical resource for code compliance questions, "
        "providing professional guidance when issues arise."
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
        # GC / CM: inspection pitch only, no plan review (rules § 0-C)
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
        if is_plan_review_focus:
            # Early-stage Developer/Owner: lead with Plan Review
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce Building Code "
                f"Consulting LLC (BCC) as a resource for {company}'s Third-Party Plan Review "
                f"and Code Compliance Inspection needs.",
                "",
                f"BCC is a DC-based firm specializing in Third-Party Plan Review and Code "
                f"Compliance Inspections. At this stage of the project, our plan review services "
                f"can help identify and resolve code issues before submission — saving time and "
                f"avoiding costly revision cycles. A few highlights:",
                "",
                bullet_expertise,
                "",
                "Plan Review Services: We provide expedited Third-Party Plan Review for DC and "
                "nationwide jurisdictions. Our reviews identify code deficiencies before "
                "submission, reducing agency review cycles and keeping your schedule on track.",
                "",
                bullet_billing,
                "",
                f"We are not submitting a formal proposal at this stage, but if you would like "
                f"to learn more about how BCC can support {project_name} through plan review or "
                f"future inspections, we would welcome the conversation.",
                "",
                "Are you open to a quick 5-minute call?",
            ]
        else:
            # Later-stage Developer/Owner: lead with Inspections, note plan review
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
        if is_plan_review_focus:
            # Early-stage Architect: lead with peer review / plan review
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce Building Code "
                f"Consulting LLC (BCC). We frequently collaborate with architects on Third-Party "
                f"Plan Review and peer review for DC projects — particularly at the design stage "
                f"when code issues are most efficiently resolved.",
                "",
                f"BCC is a DC-based firm specializing in DC Third-Party Code Compliance and Plan "
                f"Review. A few highlights relevant to {company}:",
                "",
                bullet_expertise,
                "",
                "Plan Review and Peer Review: We provide expedited Third-Party Plan Review for "
                "DC and nationwide jurisdictions. Our team can review drawings for code compliance "
                "before submission — catching issues early and protecting your project schedule.",
                "",
                bullet_billing,
                "",
                f"We are not submitting a formal proposal at this stage, but would welcome the "
                f"opportunity to discuss how BCC can support {project_name} during design and "
                f"into construction.",
                "",
                "Are you open to a quick 5-minute call?",
            ]
        else:
            # Later-stage Architect: peer review + inspections
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
        # Default: conservative pitch based on stage focus
        if is_plan_review_focus:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce Building Code "
                f"Consulting LLC (BCC) as a resource for Third-Party Plan Review and Inspection needs.",
                "",
                "BCC is a DC-based engineering firm specializing in Washington, D.C. Third-Party "
                "Code Compliance Plan Review and Inspections. A few reasons we may be a strong fit:",
                "",
                bullet_expertise,
                "",
                "Plan Review Services: We offer expedited Third-Party Plan Review for DC and "
                "nationwide jurisdictions — helping identify code issues before submission.",
                "",
                bullet_billing,
                "",
                "We are not submitting a formal proposal at this stage, but if you are exploring "
                "plan review or inspection resources for this project, we would welcome a brief conversation.",
                "",
                "Are you open to a quick 5-minute call?",
            ]
        else:
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

    # Load sent_log to avoid re-contacting anyone emailed in the last 60 days
    import csv as _csv
    from datetime import timedelta as _td
    _recently_emailed: set[str] = set()
    _cutoff = datetime.now() - _td(days=60)
    try:
        with open(BASE_DIR / "sent_log.csv", newline="", encoding="utf-8") as _f:
            for row in _csv.DictReader(_f):
                _ts_str = row.get("sent_at") or row.get("followup_sent_at") or ""
                try:
                    from datetime import timezone as _tz
                    _ts = datetime.fromisoformat(_ts_str.replace("Z", "+00:00"))
                    if _ts.tzinfo:
                        _ts = _ts.replace(tzinfo=None)  # make naive for comparison
                except Exception:
                    _ts = None
                if _ts and _ts >= _cutoff:
                    _recently_emailed.add((row.get("contact_email") or "").strip().lower())
    except FileNotFoundError:
        pass
    if _recently_emailed:
        print(f"  Dedup: {len(_recently_emailed)} contacts emailed in the last 60 days — will skip.")

    emails: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (email_lower, project)

    def _add_email(project_name: str, company: str, role: str,
                   contact_name: str, contact_role: str, email_addr: str, phone: str,
                   service_focus: str = "Inspection") -> None:
        key = (email_addr.lower(), project_name)
        if key in seen:
            return
        # Skip contacts we've already emailed in the past 60 days
        if email_addr.lower() in _recently_emailed:
            return
        seen.add(key)
        # Adjust subject based on service focus
        if "Plan Review" in service_focus and not _role_is_gc_or_cm(role):
            subject = f"Third-Party Plan Review & Inspection Services for {project_name} | Building Code Consulting LLC"
        else:
            subject = f"Third-Party Inspection Services for {project_name} | Building Code Consulting LLC"
        body = _generate_email_body(contact_name, company, role, project_name, service_focus)
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

        stage_text = lead.get("stage") or lead.get("construction_start") or ""
        service_focus, _ = _stage_service_focus(stage_text)

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
            role_mapped = _map_cw_role(role)
            _add_email(project_name, company, role_mapped, contact_name, role, email_addr, "", service_focus)

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
                _add_email(project_name, company, role, contact_name, contact_role, email_addr, phone, service_focus)

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
    """
    Send a summary to Telegram.
    When > 20 drafts, skip individual previews (too many for Telegram rate limits).
    Drafts are reviewed locally via the Top-100 file + send_cw_outreach.py.
    """
    import time

    print(f"\n{'='*60}")
    print("Phase 7: Sending Email Drafts Summary to Telegram")
    print(f"{'='*60}")

    by_company: dict[str, list[dict]] = {}
    for em in email_drafts:
        by_company.setdefault(em["company"], []).append(em)

    # Build compact company list (max 50 lines to stay under TG limit)
    lines = []
    for company, ems in sorted(by_company.items())[:50]:
        contacts = ", ".join(e["contact_name"] for e in ems if e["contact_name"])
        lines.append(f"• {company}: {contacts or '(no name)'}")
    company_list = "\n".join(lines)
    if len(by_company) > 50:
        company_list += f"\n... and {len(by_company) - 50} more companies"

    tg_message(
        f"📧 *BCC CW Cold Outreach Drafts — {TODAY}*\n\n"
        f"✅ {len(email_drafts)} drafts generated across {len(by_company)} companies.\n\n"
        f"{company_list}\n\n"
        f"📂 Drafts saved locally: Pending_Approval/Outbound/CW_*.md\n"
        f"📋 Review the Top-100 list (attached above) to decide who to send.\n\n"
        f"To send all:\n`python send_cw_outreach.py --all --attachment \"<pdf_path>\"`\n"
        f"To preview without sending:\n`python send_cw_outreach.py --dry-run`\n"
        f"To filter by company:\n`python send_cw_outreach.py --company \"Carr\"`"
    )

    # Only send individual previews if count is small enough
    MAX_INDIVIDUAL_PREVIEWS = 15
    if len(email_drafts) <= MAX_INDIVIDUAL_PREVIEWS:
        for em, fpath in zip(email_drafts, saved_paths):
            preview = (
                f"📨 *{em['company']}* ({em['company_role']})\n"
                f"Project: {em['project']}\n"
                f"To: {em['contact_name']} <{em['to_email']}>"
                + (f"\nPhone: {em['phone']}" if em["phone"] else "")
                + f"\nSubject: {em['subject']}\n\n---\n{em['body'][:600]}"
            )
            tg_message(preview)
            time.sleep(1.5)  # stay well under Telegram rate limits

    print(f"Phase 7 complete: summary sent. {len(email_drafts)} drafts ready locally.")


# ─── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(
        description="ConstructionWire Full DC Leads Pipeline — scrape, research, generate emails"
    )
    ap.add_argument("--pages",        type=int, default=10, help="Max list pages to scrape (default: 10)")
    ap.add_argument("--headless",     action="store_true",  help="Run Playwright browser headless")
    ap.add_argument("--max-contacts", type=int, default=3,  help="Max contacts per company (default: 3)")
    ap.add_argument("--skip-research",action="store_true",  help="Use only CW detail-page contacts (no deep search)")
    ap.add_argument("--skip-telegram",action="store_true",  help="Skip all Telegram sends (local output only)")
    ap.add_argument(
        "--stages", default=",".join(str(s) for s in DEFAULT_STAGES),
        help="Comma-separated CW stage codes (default: 1,2,3,4,5,6,7 = all stages)"
    )
    # ── Checkpoint / resume flags ──────────────────────────────────────────────
    ap.add_argument("--resume",     action="store_true", help="Resume from last saved checkpoint")
    ap.add_argument("--from-phase", type=int, default=0, metavar="N",
                    help="Skip to phase N using checkpoint data (1=scrape…7=tg-drafts)")
    ap.add_argument("--status",     action="store_true", help="Show checkpoint status and exit")
    ap.add_argument("--clear-checkpoint", action="store_true", help="Delete checkpoint file and exit")
    args = ap.parse_args()

    # ── Checkpoint utility commands ───────────────────────────────────────────
    if args.status:
        cp = _checkpoint_load()
        if not cp:
            print("No checkpoint found. Pipeline has not been started or was completed cleanly.")
            return 0
        print(f"Checkpoint status (last updated: {cp.get('last_updated', 'unknown')}):")
        for i, (phase, key) in enumerate([
            (1, "phase1_done"), (2, "phase2_done"), (3, "phase3_done"),
            (4, "phase4_done"), (5, "phase5_done"), (6, "phase6_done"), (7, "phase7_done"),
        ], 1):
            status = "✅ done" if cp.get(key) else "⏳ pending"
            label = ["scrape", "research", "report", "telegram report",
                     "generate emails", "save drafts", "telegram drafts"][i - 1]
            print(f"  Phase {phase} ({label}): {status}")
        if cp.get("phase2_researched"):
            print(f"  Phase 2 partial: {len(cp['phase2_researched'])} companies researched so far")
        return 0

    if args.clear_checkpoint:
        _checkpoint_clear()
        return 0

    try:
        stages = [int(s.strip()) for s in args.stages.split(",") if s.strip()]
    except ValueError:
        print(f"ERROR: --stages must be comma-separated integers, got: {args.stages}")
        return 1

    # ── Determine resume point ─────────────────────────────────────────────────
    cp: dict = {}
    resume_from: int = 1  # default: run everything from phase 1

    if args.resume or args.from_phase:
        cp = _checkpoint_load()
        if not cp and not args.from_phase:
            print("No checkpoint found — starting fresh.")
        elif cp:
            if args.from_phase:
                resume_from = args.from_phase
                print(f"Resuming from phase {resume_from} (forced via --from-phase).")
            else:
                resume_from = _checkpoint_resume_phase(cp)
                print(f"Resuming from phase {resume_from} (last updated: {cp.get('last_updated', '?')}).")
        if args.from_phase:
            resume_from = args.from_phase

    # Preserve the original timestamp across resume runs (keeps file names consistent)
    now_str = cp.get("now_str", NOW_STR)

    if resume_from == 1:
        # Fresh run: initialize checkpoint with args
        _checkpoint_save({
            "now_str": now_str,
            "args": {
                "pages": args.pages, "stages": stages, "headless": args.headless,
                "max_contacts": args.max_contacts, "skip_research": args.skip_research,
            },
        })

    # ── Phase 1: Scrape ───────────────────────────────────────────────────────
    if resume_from <= 1:
        leads = asyncio.run(
            phase1_scrape_leads(headless=args.headless, max_pages=args.pages, stages=stages)
        )
        if not leads:
            print("No leads found. Exiting.")
            return 1
        raw_path = BASE_DIR / f"cw_leads_raw_{now_str}.json"
        raw_path.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Raw leads JSON: {raw_path.name}")
        _checkpoint_save({"phase1_done": True, "phase1_leads_file": str(raw_path)})
    else:
        leads_file = cp.get("phase1_leads_file", "")
        if not leads_file or not Path(leads_file).exists():
            print("ERROR: Checkpoint phase1_leads_file missing or gone. Run without --resume.")
            return 1
        leads = json.loads(Path(leads_file).read_text(encoding="utf-8"))
        print(f"[RESUME] Phase 1: {len(leads)} leads loaded from {Path(leads_file).name}")

    # ── Phase 2: Research ─────────────────────────────────────────────────────
    if resume_from <= 2:
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
            # On partial resume (e.g., crashed mid-phase-2), reload partial results
            existing = cp.get("phase2_company_research", {}) if resume_from == 2 else {}
            skip_cos = set(cp.get("phase2_researched", [])) if resume_from == 2 else set()
            company_research = phase2_research_companies(
                leads, max_contacts=args.max_contacts,
                existing_research=existing, skip_companies=skip_cos,
            )
        _checkpoint_save({"phase2_done": True, "phase2_company_research": company_research})
    else:
        company_research = cp.get("phase2_company_research", {})
        print(f"[RESUME] Phase 2: {len(company_research)} companies loaded from checkpoint")

    # ── Phase 3: Report + Top-100 ─────────────────────────────────────────────
    if resume_from <= 3:
        report_md = phase3_compile_report(leads, company_research)
        report_path = BASE_DIR / f"DC_Leads_Report_{now_str}.md"
        report_path.write_text(report_md, encoding="utf-8")
        print(f"\nReport saved: {report_path.name}")
        summary_end = report_md.find("## Detailed Contacts per Project")
        print("\n" + ("=" * 60))
        print(report_md[:summary_end] if summary_end > 0 else report_md[:2000])

        top100_md = phase_rank_top100(leads, company_research)
        top100_path = BASE_DIR / f"DC_Top100_{now_str}.md"
        top100_path.write_text(top100_md, encoding="utf-8")
        print(f"Top-100 report saved: {top100_path.name}")
        _checkpoint_save({
            "phase3_done": True,
            "phase3_report_file": str(report_path),
            "phase3b_done": True,
            "phase3b_top100_file": str(top100_path),
        })
    else:
        report_path = Path(cp.get("phase3_report_file", ""))
        top100_path = Path(cp.get("phase3b_top100_file", ""))
        report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        print(f"[RESUME] Phase 3: report={report_path.name}, top100={top100_path.name}")

    # ── Phase 4: Telegram report ──────────────────────────────────────────────
    if resume_from <= 4 and not args.skip_telegram:
        phase4_send_report_telegram(report_md, report_path)
        tg_message("📋 Top-100 prioritized leads list attached (score = stage priority + value + contact quality):")
        tg_document(top100_path, caption=f"Top100 leads — {TODAY}")
        _checkpoint_save({"phase4_done": True})
    elif args.skip_telegram:
        print("[--skip-telegram] Skipping Telegram report.")
    else:
        print("[RESUME] Phase 4: Telegram report already sent.")

    # ── Phase 5: Generate emails ──────────────────────────────────────────────
    if resume_from <= 5:
        email_drafts = phase5_generate_emails(leads, company_research)
        if not email_drafts:
            print("\nNo email drafts generated (no contacts with emails found).")
            print("Tip: Run without --skip-research or check CW detail pages have contacts.")
            _checkpoint_clear()
            return 0
        _checkpoint_save({"phase5_done": True, "phase5_email_count": len(email_drafts)})
    else:
        # Re-generate emails from loaded data (drafts may have been deleted)
        email_drafts = phase5_generate_emails(leads, company_research)
        print(f"[RESUME] Phase 5: {len(email_drafts)} emails re-generated from checkpoint data")

    # ── Phase 6: Save drafts ──────────────────────────────────────────────────
    if resume_from <= 6:
        saved_paths = phase6_save_drafts(email_drafts)
        _checkpoint_save({"phase6_done": True})
    else:
        saved_paths = sorted(OUTBOUND_DIR.glob("CW_*.md"))
        print(f"[RESUME] Phase 6: {len(saved_paths)} draft files found in Outbound/")

    # ── Phase 7: Telegram drafts ──────────────────────────────────────────────
    if resume_from <= 7 and not args.skip_telegram:
        phase7_send_drafts_telegram(email_drafts, saved_paths)
        _checkpoint_save({"phase7_done": True})
    elif args.skip_telegram:
        print("[--skip-telegram] Skipping Telegram drafts send.")
    else:
        print("[RESUME] Phase 7: Telegram drafts already sent.")

    # ── Done ──────────────────────────────────────────────────────────────────
    _checkpoint_clear()
    print(f"\n{'='*60}")
    print("Pipeline COMPLETE")
    print(f"  Leads scraped:        {len(leads)}")
    print(f"  Companies researched: {len(company_research)}")
    print(f"  Email drafts:         {len(email_drafts)}")
    print(f"  Report:               {report_path.name}")
    print(f"  Top-100 list:         {top100_path.name}")
    print(f"  Drafts:               Pending_Approval/Outbound/CW_*.md")
    print(f"\nNext step — after reviewing drafts:")
    print(f"  python send_cw_outreach.py --all --attachment \"<pdf_path>\"")
    print(f"  python daily_sender.py    # rate-limited: max 20/day")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
