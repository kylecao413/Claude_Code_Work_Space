"""
bc_batch_scrape.py — Batch scrape BuildingConnected bid invites.

Logs into BC, navigates to bid invites page, finds project URLs,
matches against a target list, and scrapes each project's details.

Usage:
    python bc_batch_scrape.py                    # headful (visible browser)
    python bc_batch_scrape.py --headless         # headless mode
    python bc_batch_scrape.py --screenshots      # save debug screenshots

Output: bc_batch_leads.json with all project details.
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

# Two-step login: BC_EMAIL goes into BC login form → redirects to Autodesk →
# BC_USERNAME + BC_PASSWORD go into Autodesk login form
BC_EMAIL = os.getenv("BC_EMAIL", "").strip().strip('"')
BC_USERNAME = os.getenv("BC_USERNAME", "").strip().strip('"')
BC_PASSWORD = os.getenv("BC_PASSWORD", "").strip().strip('"')

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / ".buildingconnected_cookies.json"
OUTPUT_FILE = BASE_DIR / "bc_batch_leads.json"

# ── Target projects to find (from user's list) ──────────────────────────────
TARGET_PROJECTS = [
    {"name": "GPO FM Modernization", "gc": "PWC Companies", "deadline": "March 18, 2026"},
    {"name": "Washington Endometriosis", "gc": "HBW Construction", "deadline": "March 2, 2026"},
    {"name": "800 Connecticut Ave Lobby Renovation", "gc": "HBW Construction", "deadline": "March 2, 2026"},
    {"name": "DuFour Center Locker Room Renovation", "gc": "HBW Construction", "deadline": ""},
    {"name": "Union Station Parking Garage Generator Room Upgrade", "gc": "HBW Construction", "deadline": ""},
    {"name": "1300 Girard Street NW", "gc": "PWC Companies", "deadline": ""},
    {"name": "1999 K St Whitebox", "gc": "HBW Construction", "deadline": ""},
    {"name": "GPO - Bldg. B Garage Rood & Skylight Replacement", "gc": "IMEC Group, LLC", "deadline": ""},
    {"name": "Ward 8 Senior Center", "gc": "PARADIGM CONTRACTORS LLC", "deadline": ""},
    {"name": "Garage - Washington, DC", "gc": "Elder-Jones, Inc.", "deadline": ""},
    {"name": "DuFour Center Office Renovation", "gc": "HBW Construction", "deadline": ""},
    {"name": "Office Images DC", "gc": "HBW Construction", "deadline": ""},
    {"name": "Demolition Blanchard Hall Building 1302 - JBAB, DC", "gc": "Desbuild, Inc.", "deadline": ""},
    {"name": "1st and M Lobby Renovations", "gc": "PWC Companies", "deadline": ""},
    {"name": "Call Your Mother - DC", "gc": "Englewood Construction, Inc.", "deadline": ""},
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


async def _save_cookies(context) -> None:
    try:
        cookies = await context.cookies()
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
    except Exception:
        pass


async def _do_login(page, headless: bool = False) -> bool:
    """
    Two-step BC login flow:
      Step 1: BC login page — enter BC_EMAIL (Gmail), click NEXT
      Step 2: Redirects to Autodesk login — enter BC_USERNAME + BC_PASSWORD
    """
    if not BC_EMAIL or not BC_PASSWORD:
        if headless:
            print("[BC] No credentials. Set BC_EMAIL/BC_USERNAME/BC_PASSWORD in .env", file=sys.stderr)
            return False
        # Manual fallback
        print("[BC] No credentials. Opening browser for manual login (5 min timeout)...", flush=True)
        await page.goto("https://app.buildingconnected.com/login", wait_until="domcontentloaded", timeout=20000)
        import time
        deadline = time.time() + 300
        while time.time() < deadline:
            await page.wait_for_timeout(3000)
            if not _is_login_page(page.url):
                print(f"[BC] Manual login detected! At: {page.url}", flush=True)
                return True
        print("[BC] Manual login timeout.", file=sys.stderr)
        return False

    autodesk_user = BC_USERNAME or BC_EMAIL  # Autodesk username (may differ from BC email)

    print(f"[BC] Step 1: BC login with {BC_EMAIL}...", flush=True)
    await page.goto("https://app.buildingconnected.com/login", wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(3000)

    try:
        # ── Step 1: Fill BC email field and click NEXT ────────────────────────
        email_sel = "#emailField, input[type='email'], input[name='email'], input[name='userName']"
        await page.wait_for_selector(email_sel, timeout=10000)
        await page.fill(email_sel, BC_EMAIL)
        await page.wait_for_timeout(500)

        # Click NEXT / submit to trigger Autodesk redirect
        submit_sel = "button:has-text('NEXT'), button:has-text('Next'), button:has-text('Sign in'), button[type='submit']"
        await page.click(submit_sel)
        print("[BC] Clicked NEXT on BC login, waiting for Autodesk redirect...", flush=True)
        await page.wait_for_timeout(5000)

        # ── Step 2: Autodesk login page ───────────────────────────────────────
        # After clicking NEXT, BC redirects to Autodesk Identity (accounts.autodesk.com)
        current_url = page.url
        print(f"[BC] Step 2: Now at {current_url}", flush=True)

        # Save screenshot for debugging
        await page.screenshot(path=str(BASE_DIR / "bc_debug_autodesk_login.png"))

        # Autodesk login may show username field first, then password
        # Try common Autodesk login selectors
        autodesk_user_sels = [
            "#userName",
            "input[name='userName']",
            "input[name='username']",
            "input[type='email']",
            "#emailField",
            "input[name='email']",
            "input[name='loginfmt']",  # Microsoft-style
        ]
        filled_user = False
        for sel in autodesk_user_sels:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.fill(autodesk_user)
                    filled_user = True
                    print(f"[BC] Filled Autodesk username in '{sel}'", flush=True)
                    break
            except Exception:
                continue

        if not filled_user:
            # Maybe the page already has the email pre-filled, or it's a different layout
            print("[BC] Could not find Autodesk username field. Trying to proceed...", flush=True)

        await page.wait_for_timeout(500)

        # Click Next/Continue on Autodesk (some flows show username first, then password)
        try:
            next_btn = page.locator("button:has-text('Next'), button:has-text('NEXT'), button:has-text('Continue'), button:has-text('Sign in'), button[type='submit']").first
            if await next_btn.count() > 0:
                await next_btn.click()
                print("[BC] Clicked Next on Autodesk username step", flush=True)
                await page.wait_for_timeout(3000)
        except Exception:
            pass

        # Now fill password
        pw_sels = [
            "#password",
            "input[name='password']",
            "input[type='password']",
            "#passwordField",
            "input[name='passwd']",  # Microsoft-style
        ]
        filled_pw = False
        for sel in pw_sels:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.fill(BC_PASSWORD)
                    filled_pw = True
                    print(f"[BC] Filled Autodesk password in '{sel}'", flush=True)
                    break
            except Exception:
                continue

        if not filled_pw:
            print("[BC] Could not find password field!", file=sys.stderr)
            await page.screenshot(path=str(BASE_DIR / "bc_debug_no_password_field.png"))
            return False

        await page.wait_for_timeout(500)

        # Click Sign In / Submit
        sign_in_btn = page.locator("button:has-text('Sign in'), button:has-text('SIGN IN'), button:has-text('Log in'), button:has-text('Next'), button[type='submit']").first
        if await sign_in_btn.count() > 0:
            await sign_in_btn.click()
            print("[BC] Clicked Sign In on Autodesk", flush=True)
        else:
            # Try pressing Enter
            await page.keyboard.press("Enter")
            print("[BC] Pressed Enter to submit", flush=True)

        # Wait for login to complete — may need manual CAPTCHA + email 2FA code
        import time
        print("", flush=True)
        print("=" * 60, flush=True)
        print("[BC] MANUAL STEPS NEEDED IN BROWSER WINDOW:", flush=True)
        print("  1. Solve CAPTCHA if prompted (image puzzle)", flush=True)
        print("  2. Check email for Autodesk verification code", flush=True)
        print("     (sent to admin@buildingcodeconsulting.com)", flush=True)
        print("  3. Enter the code in the browser and click Next", flush=True)
        print("  Waiting up to 5 minutes...", flush=True)
        print("=" * 60, flush=True)
        deadline = time.time() + 300  # 5 minutes for CAPTCHA + 2FA
        while time.time() < deadline:
            await page.wait_for_timeout(3000)
            current_url = page.url
            if not _is_login_page(current_url):
                print(f"[BC] Login succeeded! At: {current_url}", flush=True)
                await page.screenshot(path=str(BASE_DIR / "bc_debug_after_login.png"))
                return True

        print(f"[BC] Login timed out. Still at: {page.url}", file=sys.stderr)
        await page.screenshot(path=str(BASE_DIR / "bc_debug_login_timeout.png"))
        return False

    except Exception as e:
        print(f"[BC] Login error: {e}", file=sys.stderr)
        await page.screenshot(path=str(BASE_DIR / "bc_debug_login_error.png"))
        return False


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy matching."""
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()


def _match_project(link_text: str, target: dict) -> float:
    """Score how well a link text matches a target project. Higher = better match."""
    link_norm = _normalize(link_text)
    target_norm = _normalize(target["name"])

    if not link_norm or not target_norm:
        return 0.0

    # Exact match
    if target_norm in link_norm:
        return 1.0

    # Token-based matching: what fraction of target tokens appear in link text
    target_tokens = set(target_norm.split())
    link_tokens = set(link_norm.split())

    if not target_tokens:
        return 0.0

    # Remove very common words
    stop_words = {"the", "a", "an", "of", "in", "at", "for", "and", "or", "dc", "washington"}
    target_significant = target_tokens - stop_words
    if not target_significant:
        target_significant = target_tokens

    matched = target_significant & link_tokens
    score = len(matched) / len(target_significant)

    return score


async def _find_opportunity_links(page, save_screenshots: bool = False) -> list[dict]:
    """
    Navigate to BC pages and find all opportunity/bid links.
    Returns list of {href, text} dicts.
    """
    all_links = []

    # Try multiple URL patterns for the bid invitations page
    urls_to_try = [
        "https://app.buildingconnected.com/projects",
        "https://app.buildingconnected.com/bid-board",
        "https://app.buildingconnected.com/bids",
        "https://app.buildingconnected.com/",
    ]

    for url in urls_to_try:
        print(f"[BC] Trying: {url}", flush=True)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(4000)

            if _is_login_page(page.url):
                print(f"  Redirected to login, skipping...")
                continue

            current_url = page.url
            print(f"  Landed at: {current_url}", flush=True)

            if save_screenshots:
                ss_name = url.split("/")[-1] or "dashboard"
                await page.screenshot(path=str(BASE_DIR / f"bc_debug_{ss_name}.png"), full_page=True)

            # Extract all links with opportunity/bid patterns
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(a => ({
                        href: a.href,
                        text: a.innerText.trim().slice(0, 200)
                    })).filter(a =>
                        a.href.includes('/opportunities/') ||
                        a.href.includes('/bids/') ||
                        a.href.includes('/rfp/')
                    );
                }
            """)

            if links:
                print(f"  Found {len(links)} opportunity links", flush=True)
                all_links.extend(links)

            # Also try to scroll down to load more items (infinite scroll)
            if links:
                for scroll_attempt in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    more_links = await page.evaluate("""
                        () => {
                            const links = Array.from(document.querySelectorAll('a[href]'));
                            return links.map(a => ({
                                href: a.href,
                                text: a.innerText.trim().slice(0, 200)
                            })).filter(a =>
                                a.href.includes('/opportunities/') ||
                                a.href.includes('/bids/') ||
                                a.href.includes('/rfp/')
                            );
                        }
                    """)
                    new_count = len(more_links) - len(links)
                    if new_count > 0:
                        print(f"  Scroll {scroll_attempt+1}: found {new_count} more links", flush=True)
                        all_links.extend(more_links[len(links):])
                        links = more_links
                    else:
                        break

            if len(all_links) > 10:
                break  # Found enough, no need to try more URLs

        except Exception as e:
            print(f"  Error on {url}: {e}", flush=True)
            continue

    # Deduplicate by href
    seen = set()
    unique = []
    for link in all_links:
        href = link.get("href", "")
        if href not in seen:
            seen.add(href)
            unique.append(link)

    return unique


async def _scrape_project_page(page, url: str) -> dict:
    """
    Navigate to a BC project /info page and extract all available fields.
    Reused from bc_scrape_project.py with improvements.
    """
    print(f"  Scraping: {url}", flush=True)
    # Ensure URL ends with /info for the overview tab
    if "/info" not in url:
        url = url.rstrip("/") + "/info"

    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
    await page.wait_for_timeout(4000)

    body_text = await page.inner_text("body")

    data = {
        "url": url,
        "project_name": "",
        "client_name": "",
        "client_short": "",
        "attention": "",
        "client_email": "",
        "project_address": "",
        "project_size_sqft": "",
        "bid_due_date": "",
        "scope_description": "",
        "raw_body_text": body_text[:8000],
    }

    async def try_text(*selectors: str, attr: str = None) -> str:
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    val = (await el.get_attribute(attr) if attr else await el.inner_text()).strip()
                    if val:
                        return val
            except Exception:
                continue
        return ""

    # Project name
    data["project_name"] = await try_text(
        "h1", "[data-testid='project-name']", ".project-name", "h2"
    )

    # Address
    data["project_address"] = await try_text(
        "[data-testid='project-address']",
        "[data-field='address']",
        ".project-address",
        "address",
    )

    # GC / Client
    data["client_name"] = await try_text(
        "[data-testid='company-name']",
        "[data-field='company']",
        ".company-name",
    )
    data["client_short"] = data["client_name"].split(" - ")[0].split(",")[0].strip()

    # Bid due date
    data["bid_due_date"] = await try_text(
        "[data-testid='bid-due']",
        "[data-field='bid-date']",
        ".bid-due-date",
    )

    # Description
    data["scope_description"] = await try_text(
        "[data-testid='project-description']",
        "[data-field='description']",
        ".project-description",
        ".description-text",
    )

    # Size
    data["project_size_sqft"] = await try_text(
        "[data-field='sqft']", "[data-testid='sqft']", ".project-size"
    )

    # Contact
    data["attention"] = await try_text(
        "[data-testid='contact-name']",
        "[data-field='contact']",
        ".contact-name",
    )
    data["client_email"] = await try_text(
        "[data-testid='contact-email']",
        'a[href^="mailto:"]',
        attr="href",
    )
    if data["client_email"].startswith("mailto:"):
        data["client_email"] = data["client_email"][7:]

    # Fallback: parse body text for common patterns
    if not data["project_address"]:
        m = re.search(
            r"(\d+\s+\w[\w\s,\.]+(?:NW|NE|SW|SE|Ave|St|Blvd|Rd|Dr)[\w\s,\.]*DC\s*\d{5})",
            body_text,
        )
        if m:
            data["project_address"] = m.group(1).strip()

    if not data["client_email"]:
        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body_text)
        if m and "buildingconnected" not in m.group(0).lower():
            data["client_email"] = m.group(0)

    if not data["bid_due_date"]:
        m = re.search(
            r"(?:bid|due|deadline)[:\s]*(\w+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
            body_text,
            re.IGNORECASE,
        )
        if m:
            data["bid_due_date"] = m.group(1).strip()

    return data


async def run(headless: bool = False, save_screenshots: bool = False):
    """Main entry: login → find opportunity links → match → scrape each."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        await _load_cookies(context)
        page = await context.new_page()

        # Navigate to BC
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Login if needed
        if _is_login_page(page.url):
            print("[BC] Not logged in — attempting login...", flush=True)
            ok = await _do_login(page, headless=headless)
            if not ok:
                await browser.close()
                print("[BC] Login failed. Check BC_EMAIL and BC_PASSWORD in .env", file=sys.stderr)
                return []
            await _save_cookies(context)
        else:
            print(f"[BC] Cookie session valid. At: {page.url}", flush=True)
            await _save_cookies(context)

        # Step 1: Find all opportunity links
        print("\n[BC] === Step 1: Finding opportunity links ===", flush=True)
        links = await _find_opportunity_links(page, save_screenshots)
        print(f"\n[BC] Total unique links found: {len(links)}", flush=True)

        # Debug: save all links
        debug_links_path = BASE_DIR / "bc_debug_all_links.json"
        debug_links_path.write_text(json.dumps(links, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[BC] All links saved to {debug_links_path.name}", flush=True)

        # Step 2: Match links to target projects
        print("\n[BC] === Step 2: Matching to target projects ===", flush=True)
        matched = []
        unmatched_targets = list(TARGET_PROJECTS)

        for target in TARGET_PROJECTS:
            best_score = 0.0
            best_link = None
            for link in links:
                score = _match_project(link.get("text", ""), target)
                if score > best_score:
                    best_score = score
                    best_link = link

            if best_score >= 0.4 and best_link:
                print(f"  MATCHED ({best_score:.0%}): {target['name']}")
                print(f"    → {best_link['text'][:60]}  ({best_link['href'][:80]})")
                matched.append({"target": target, "link": best_link, "score": best_score})
                if target in unmatched_targets:
                    unmatched_targets.remove(target)
            else:
                print(f"  NO MATCH: {target['name']} (best score: {best_score:.0%})")

        print(f"\n[BC] Matched: {len(matched)}/{len(TARGET_PROJECTS)} projects", flush=True)

        if unmatched_targets:
            print(f"\n[BC] Unmatched projects ({len(unmatched_targets)}):")
            for t in unmatched_targets:
                print(f"  - {t['name']} ({t['gc']})")

        # Step 3: Scrape each matched project
        print(f"\n[BC] === Step 3: Scraping {len(matched)} matched projects ===", flush=True)
        results = []
        for i, m in enumerate(matched, 1):
            target = m["target"]
            link = m["link"]
            href = link["href"]
            print(f"\n[{i}/{len(matched)}] {target['name']}", flush=True)

            if save_screenshots:
                ss_name = re.sub(r'[^a-z0-9]', '_', target['name'].lower())[:40]
                await page.screenshot(path=str(BASE_DIR / f"bc_project_{ss_name}.png"))

            try:
                data = await _scrape_project_page(page, href)
                # Fill in known data from target list if scraper missed it
                if not data.get("client_name"):
                    data["client_name"] = target["gc"]
                    data["client_short"] = target["gc"].split(",")[0].split(" - ")[0].strip()
                if not data.get("bid_due_date") and target.get("deadline"):
                    data["bid_due_date"] = target["deadline"]
                data["target_name"] = target["name"]
                data["target_gc"] = target["gc"]
                data["match_score"] = m["score"]
                results.append(data)
                print(f"  Name: {data.get('project_name', 'N/A')}")
                print(f"  Client: {data.get('client_name', 'N/A')}")
                print(f"  Address: {data.get('project_address', 'N/A')}")
                print(f"  Contact: {data.get('attention', 'N/A')} <{data.get('client_email', '')}>")
            except Exception as e:
                print(f"  ERROR scraping: {e}", flush=True)
                # Still record the project with whatever we know
                results.append({
                    "url": href,
                    "project_name": target["name"],
                    "client_name": target["gc"],
                    "target_name": target["name"],
                    "target_gc": target["gc"],
                    "error": str(e),
                })

        # Also add unmatched targets as entries with empty data (for manual URL entry)
        for target in unmatched_targets:
            results.append({
                "url": "",
                "project_name": target["name"],
                "client_name": target["gc"],
                "client_short": target["gc"].split(",")[0].strip(),
                "target_name": target["name"],
                "target_gc": target["gc"],
                "bid_due_date": target.get("deadline", ""),
                "match_score": 0.0,
                "status": "UNMATCHED — needs manual URL",
            })

        await _save_cookies(context)
        await browser.close()

        # Save results
        output = []
        for r in results:
            entry = {k: v for k, v in r.items() if k != "raw_body_text"}
            output.append(entry)

        OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[BC] Results saved to {OUTPUT_FILE.name}")
        print(f"[BC] Total: {len(output)} projects ({len(matched)} matched, {len(unmatched_targets)} unmatched)")

        # Also save raw body text for debugging
        debug_raw = BASE_DIR / "bc_batch_raw_bodies.json"
        raw_bodies = {r.get("target_name", ""): r.get("raw_body_text", "")[:3000] for r in results}
        debug_raw.write_text(json.dumps(raw_bodies, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[BC] Raw body text saved to {debug_raw.name} (for debugging)")

        return output


def main():
    headless = "--headless" in sys.argv
    screenshots = "--screenshots" in sys.argv
    results = asyncio.run(run(headless=headless, save_screenshots=screenshots))
    if not results:
        print("\n[BC] No results. Check login credentials and try again.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Summary: {len(results)} projects")
    print(f"{'='*60}")
    for r in results:
        status = r.get("status", "OK")
        name = r.get("project_name") or r.get("target_name", "?")
        gc = r.get("client_name") or r.get("target_gc", "?")
        addr = r.get("project_address", "")
        print(f"  [{status}] {name} | {gc} | {addr[:40]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
