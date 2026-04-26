"""
bc_scrape_all.py — Scrape all matched BC project pages using known URLs.
Parses body text (more reliable than CSS selectors for BC's React app).

Uses saved cookies from bc_batch_scrape.py login.
Output: bc_all_projects.json
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / ".buildingconnected_cookies.json"
OUTPUT_FILE = BASE_DIR / "bc_all_projects.json"

# Known project URLs from bc_bidboard_scrape.py matching
PROJECTS_TO_SCRAPE = [
    {"target_name": "GPO FM Modernization", "gc": "PWC Companies", "deadline": "March 18, 2026",
     "url": "https://app.buildingconnected.com/opportunities/69975f1ac67f4fe52988dadc"},
    {"target_name": "Washington Endometriosis", "gc": "HBW Construction", "deadline": "March 2, 2026",
     "url": "https://app.buildingconnected.com/opportunities/6995e24cc69ad27f7e0419f6"},
    {"target_name": "800 Connecticut Ave Lobby Renovation", "gc": "HBW Construction", "deadline": "March 2, 2026",
     "url": "https://app.buildingconnected.com/opportunities/69989d96b6ea6f4c88c2d683"},
    {"target_name": "DuFour Center Locker Room Renovation", "gc": "HBW Construction", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/6996244d135f10fd3b5e3674"},
    {"target_name": "Union Station Parking Garage Generator Room Upgrade", "gc": "HBW Construction", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/69961cc3f218dba86210d72d"},
    {"target_name": "1300 Girard Street NW", "gc": "PWC Companies", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/698ccd49bf8c4ad543f56491"},
    {"target_name": "1999 K St Whitebox", "gc": "HBW Construction", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/698e08ede6668f8aeb298f00"},
    {"target_name": "GPO - Bldg. B Garage Rood & Skylight Replacement", "gc": "IMEC Group, LLC", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/6988a5b3e8c64c527c21464a"},
    {"target_name": "Ward 8 Senior Center", "gc": "PARADIGM CONTRACTORS LLC", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/698223fb67242900bc26b002"},
    {"target_name": "Garage - Washington, DC", "gc": "Elder-Jones, Inc.", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/69724efb5c75142f6fa698bf"},
    {"target_name": "1st and M Lobby Renovations", "gc": "PWC Companies", "deadline": "",
     "url": "https://app.buildingconnected.com/opportunities/694457f7739cad20f748b9a7"},
    # --- NOT FOUND on BC (need manual URLs or skip) ---
    # DuFour Center Office Renovation — HBW Construction
    # Office Images DC — HBW Construction
    # Demolition Blanchard Hall Building 1302 - JBAB, DC — Desbuild, Inc.
    # Call Your Mother - DC — Englewood Construction, Inc.
]


def _is_login_page(url: str) -> bool:
    return any(k in url.lower() for k in ("login", "signin", "auth0", "autodesk.com/authenticate"))


async def _load_cookies(context) -> bool:
    if not COOKIES_FILE.exists():
        return False
    try:
        cookies = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
        await context.add_cookies(cookies)
        return True
    except Exception:
        return False


def _parse_body_text(body: str) -> dict:
    """
    Parse BC project page body text to extract structured fields.
    BC pages have a predictable text layout:
      Client > [Company] > [Contact] > [Phone] > [Email]
      Project Name > [Name]
      Location > [Address]
      Project Size > [Size]
      Project Information > [Description]
    """
    data = {
        "project_name": "",
        "client_name": "",
        "client_short": "",
        "attention": "",
        "client_email": "",
        "client_phone": "",
        "project_address": "",
        "project_size_sqft": "",
        "bid_due_date": "",
        "scope_description": "",
        "trade": "",
        "invited_date": "",
    }

    # Project Name: appears after "Project Name\n" in General info section
    m = re.search(r'Project Name\n(.+?)(?:\n|$)', body)
    if m:
        data["project_name"] = m.group(1).strip()

    # Location: appears after "Location\n"
    m = re.search(r'Location\n(.+?)(?:\n|$)', body)
    if m:
        addr = m.group(1).strip()
        # Remove "United States of America" suffix
        addr = re.sub(r',?\s*United States of America\s*$', '', addr).strip()
        data["project_address"] = addr

    # Project Size: appears after "Project Size\n"
    m = re.search(r'Project Size\n(.+?)(?:\n|$)', body)
    if m:
        size = m.group(1).strip()
        if size != "--":
            data["project_size_sqft"] = size

    # Project Information (description): appears after "Project Information\n"
    m = re.search(r'Project Information\n(.+?)(?:\nTrade Specific Instructions|\nRelated organizations|\n$)', body, re.DOTALL)
    if m:
        desc = m.group(1).strip()
        if desc != "--":
            data["scope_description"] = desc

    # Trade: appears after "Trade Name(s)\n"
    m = re.search(r'Trade Name\(s\)\n(.+?)(?:\n|$)', body)
    if m:
        data["trade"] = m.group(1).strip()

    # Due Date: appears after "Date Due\n" or "Due date\n"
    m = re.search(r'(?:Date Due|Due date)\n(.+?)(?:\n|$)', body)
    if m:
        data["bid_due_date"] = m.group(1).strip()

    # Client/Company: appears in the Client section
    # Pattern: "Client\nBidding to multiple clients?...\n[Company Name]\n[Initials]\n[Contact Name]\n...\n[Email]"
    client_block = re.search(
        r'Client\nBidding to multiple clients\?[^\n]*\n(.+?)(?:\nProject Details|\nInvited on)',
        body, re.DOTALL
    )
    if client_block:
        lines = [l.strip() for l in client_block.group(1).strip().split('\n') if l.strip()]
        if lines:
            # First substantial line is company name
            data["client_name"] = lines[0]
            data["client_short"] = lines[0].split(" - ")[0].split(",")[0].strip()

    # Contact name: look for a name between company and email
    # Pattern: 2-letter initials, then full name, then phone/email
    m = re.search(r'\n([A-Z]{2})\n([A-Za-z]+ [A-Za-z]+)\s*\n?\s*\|\s*\n?(\+?1?[\s-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})\s*\n?\s*\|\s*\n?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', body)
    if m:
        data["attention"] = m.group(2).strip()
        data["client_phone"] = m.group(3).strip()
        data["client_email"] = m.group(4).strip()
    else:
        # Try just finding email
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', body)
        bc_emails = [e for e in emails if "buildingconnected" not in e.lower()]
        if bc_emails:
            data["client_email"] = bc_emails[0]

        # Try finding contact name near email
        if data["client_email"]:
            idx = body.find(data["client_email"])
            if idx > 0:
                before = body[max(0, idx-200):idx]
                # Look for "Name\n | \n" pattern before email
                name_lines = [l.strip() for l in before.split('\n') if l.strip() and len(l.strip()) > 3]
                for line in reversed(name_lines):
                    if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line) and '@' not in line and '|' not in line:
                        data["attention"] = line
                        break

        # Try finding phone
        phones = re.findall(r'\+?1?[\s-]?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}', body)
        if phones:
            data["client_phone"] = phones[0].strip()

    # Invited date
    m = re.search(r'Invited on\s+(\d{1,2}/\d{1,2}/\d{4})', body)
    if m:
        data["invited_date"] = m.group(1).strip()
    else:
        m = re.search(r'Date Invited\n(.+?)(?:\n|$)', body)
        if m:
            data["invited_date"] = m.group(1).strip()

    return data


async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        await _load_cookies(context)
        page = await context.new_page()

        # Check login
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)
        if _is_login_page(page.url):
            print("NOT LOGGED IN. Run bc_batch_scrape.py first.", file=sys.stderr)
            await browser.close()
            return

        print(f"Logged in. At: {page.url}", flush=True)

        results = []
        for i, proj in enumerate(PROJECTS_TO_SCRAPE, 1):
            name = proj["target_name"]
            url = proj["url"]
            print(f"\n[{i}/{len(PROJECTS_TO_SCRAPE)}] {name}", flush=True)

            # Navigate to project info page
            info_url = url.rstrip("/") + "/info" if "/info" not in url else url
            try:
                await page.goto(info_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(4000)

                body = await page.inner_text("body")

                # Parse structured data from body text
                data = _parse_body_text(body)
                data["url"] = info_url
                data["target_name"] = name
                data["target_gc"] = proj["gc"]
                data["raw_body"] = body[:5000]

                # Use target GC as fallback if not extracted
                if not data["client_name"]:
                    data["client_name"] = proj["gc"]
                    data["client_short"] = proj["gc"].split(",")[0].strip()

                if not data["bid_due_date"] and proj.get("deadline"):
                    data["bid_due_date"] = proj["deadline"]

                print(f"  Project: {data['project_name']}", flush=True)
                print(f"  Client:  {data['client_name']}", flush=True)
                print(f"  Contact: {data['attention']} <{data['client_email']}>", flush=True)
                print(f"  Phone:   {data['client_phone']}", flush=True)
                print(f"  Address: {data['project_address']}", flush=True)
                print(f"  Size:    {data['project_size_sqft']}", flush=True)
                print(f"  Due:     {data['bid_due_date']}", flush=True)
                print(f"  Desc:    {data['scope_description'][:100]}...", flush=True)

                results.append(data)

            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                results.append({
                    "url": info_url,
                    "target_name": name,
                    "target_gc": proj["gc"],
                    "error": str(e),
                })

        # Save results (without raw_body for cleaner output)
        clean_results = []
        raw_bodies = {}
        for r in results:
            raw_bodies[r.get("target_name", "")] = r.pop("raw_body", "")
            clean_results.append(r)

        OUTPUT_FILE.write_text(json.dumps(clean_results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"Saved {len(clean_results)} projects to {OUTPUT_FILE.name}")

        # Save raw bodies for debugging
        (BASE_DIR / "bc_raw_bodies_debug.json").write_text(
            json.dumps(raw_bodies, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY — {len(clean_results)} projects scraped")
        print(f"{'='*60}")
        for r in clean_results:
            status = "ERROR" if r.get("error") else "OK"
            print(f"  [{status}] {r.get('project_name') or r.get('target_name')}")
            if not r.get("error"):
                print(f"         GC: {r.get('client_name')} | {r.get('attention')} <{r.get('client_email')}>")
                print(f"         Addr: {r.get('project_address')}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
