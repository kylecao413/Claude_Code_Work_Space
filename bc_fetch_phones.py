"""
bc_fetch_phones.py — Fetch phone numbers for BC proposal contacts.

Logs into BuildingConnected, navigates to the Bids section,
opens each submitted bid, and extracts the contact phone number.

Usage:
    python bc_fetch_phones.py             # headless=False (visible browser)
    python bc_fetch_phones.py --headless  # headless mode
"""
import asyncio
import json
import os
import sys
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BC_EMAIL    = os.getenv("BC_EMAIL", "").strip()
BC_PASSWORD = os.getenv("BC_PASSWORD", "").strip()

BASE_DIR     = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / ".buildingconnected_cookies.json"

# Known contacts from submitted proposals — we'll try to match by name/email
TARGET_CONTACTS = [
    {"name": "Alex Pauley",       "company": "Keller Brothers",         "email": "apauley@kellerbrothers.com"},
    {"name": "Tariq Hamid",       "company": "DGMTS",                   "email": "thamid@dullesgeotechnical.com"},
    {"name": "Zichang Zhang",     "company": "DGMTS",                   "email": "zzhang@dullesgeotechnical.com"},
    {"name": "Angel Colon",       "company": "HBW Construction",        "email": ""},
    {"name": "Seydou Tounkara",   "company": "Whiting-Turner",          "email": ""},
    {"name": "Paul White",        "company": "Infinity Building",       "email": ""},
    {"name": "Rock Meng",         "company": "Capitol FPE",             "email": ""},
    {"name": "Alex Chu",          "company": "JP Solutions",            "email": ""},
    {"name": "Steven Ferguson",   "company": "Hamel Builders",          "email": ""},
    {"name": "Matt Burich",       "company": "Built With Benchmark",    "email": ""},
    {"name": "Bryan Kerr",        "company": "Cox & Company",           "email": ""},
    {"name": "Alex Dorsey",       "company": "HBW Construction",        "email": ""},
    {"name": "Jennifer James",    "company": "HBW Construction",        "email": ""},
    {"name": "Nicole Erdelyi",    "company": "PWC Companies",           "email": ""},
]

PHONE_RE = re.compile(r'(\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4})')


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


async def _do_login(page) -> bool:
    if not BC_EMAIL or not BC_PASSWORD:
        print("ERROR: BC_EMAIL / BC_PASSWORD not set in .env")
        return False
    print(f"Logging in as {BC_EMAIL}...")
    await page.goto("https://app.buildingconnected.com/login", wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(2000)
    try:
        email_sel = "#emailField, input[type='email'], input[name='email']"
        await page.wait_for_selector(email_sel, timeout=8000)
        await page.fill(email_sel, BC_EMAIL)
        await page.wait_for_timeout(400)
        pw_sel = "#passwordField, input[type='password'], input[name='password']"
        try:
            await page.wait_for_selector(pw_sel, timeout=4000)
            await page.fill(pw_sel, BC_PASSWORD)
        except Exception:
            await page.click("button")
            await page.wait_for_timeout(2000)
            await page.wait_for_selector(pw_sel, timeout=8000)
            await page.fill(pw_sel, BC_PASSWORD)
        await page.wait_for_timeout(400)
        submit_sel = "button:has-text('NEXT'), button:has-text('Next'), button[type='submit']"
        await page.click(submit_sel)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        if _is_login_page(page.url):
            print("Login failed — still on login page.")
            return False
        print(f"Login succeeded. At: {page.url}")
        return True
    except Exception as e:
        print(f"Login error: {e}")
        return False


async def _extract_phone_from_page(page) -> str:
    """Search the current page body for a phone number."""
    try:
        body = await page.inner_text("body")
        phones = PHONE_RE.findall(body)
        if phones:
            return phones[0]
    except Exception:
        pass
    return ""


async def _get_bids_page_and_extract(page) -> list[dict]:
    """
    Navigate to BC 'My Bids' / submitted bids section and extract
    contact info including phone numbers.
    """
    results = []

    # Try different BC bids URL patterns
    bids_urls = [
        "https://app.buildingconnected.com/bids",
        "https://app.buildingconnected.com/bids/submitted",
        "https://app.buildingconnected.com/account/bids",
        "https://app.buildingconnected.com/subcontractor/bids",
    ]

    landed = False
    for url in bids_urls:
        print(f"Trying bids URL: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            if not _is_login_page(page.url) and page.url not in ("about:blank",):
                print(f"  Landed at: {page.url}")
                landed = True
                break
        except Exception as e:
            print(f"  Failed: {e}")
            continue

    if not landed:
        print("Could not reach bids section. Trying dashboard...")
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)

    # Dump page body for debugging
    body = await page.inner_text("body")
    debug_path = BASE_DIR / "bc_bids_page_debug.txt"
    debug_path.write_text(body[:5000], encoding="utf-8")
    print(f"  Page body snippet saved to bc_bids_page_debug.txt")
    print(f"  Current URL: {page.url}")
    print(f"  Body preview: {body[:300]}")

    # Look for bid rows / links
    # Try to find all links that look like bid detail pages
    all_links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href]'))
            .map(a => ({href: a.href, text: a.innerText.trim().slice(0, 80)}))
            .filter(a => a.href.includes('/bids/') || a.href.includes('/opportunities/') || a.href.includes('/rfp/'))
    """)

    print(f"  Found {len(all_links)} bid/opportunity links")
    for link in all_links[:5]:
        print(f"    {link}")

    # For each bid link, navigate and extract contact phone
    seen_urls = set()
    for link in all_links[:30]:
        href = link.get("href", "")
        if href in seen_urls:
            continue
        seen_urls.add(href)
        try:
            print(f"  Opening: {href[:80]}")
            await page.goto(href, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            body = await page.inner_text("body")

            # Extract name, phone, email from page
            phones = PHONE_RE.findall(body)
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', body)

            if phones or emails:
                # Try to match to our known contacts
                body_lower = body.lower()
                for tc in TARGET_CONTACTS:
                    name_match = tc["name"].lower() in body_lower
                    email_match = tc["email"] and tc["email"].lower() in body_lower
                    co_match = tc["company"].lower().split()[0] in body_lower
                    if name_match or email_match:
                        phone = phones[0] if phones else ""
                        email = next((e for e in emails if "@" in e and "buildingconnected" not in e), "")
                        results.append({
                            "name": tc["name"],
                            "company": tc["company"],
                            "phone": phone,
                            "email": email or tc["email"],
                            "source_url": href,
                        })
                        print(f"  MATCH: {tc['name']} — phone: {phone}")
                        break

        except Exception as e:
            print(f"  Error on {href[:60]}: {e}")
            continue

    return results


async def run(headless: bool = False):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        await _load_cookies(context)
        page = await context.new_page()

        # Check if logged in
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        if _is_login_page(page.url):
            ok = await _do_login(page)
            if not ok:
                await browser.close()
                return
            await _save_cookies(context)

        print(f"\nLogged in. At: {page.url}")
        results = await _get_bids_page_and_extract(page)

        await _save_cookies(context)
        await browser.close()

        print(f"\n{'='*60}")
        print(f"Phone numbers found: {len(results)}")
        for r in results:
            print(f"  {r['name']:<25} {r['company']:<25} {r.get('phone','—')}")

        # Save results
        out = BASE_DIR / "bc_contact_phones.json"
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved to {out.name}")


if __name__ == "__main__":
    headless = "--headless" in sys.argv
    asyncio.run(run(headless=headless))
