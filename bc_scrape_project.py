"""
bc_scrape_project.py — Scrape a single BuildingConnected project page.

Usage:
    python bc_scrape_project.py <BC_PROJECT_URL>
    python bc_scrape_project.py https://app.buildingconnected.com/opportunities/6994c8f967a3cd6603d90248/info

Requires in .env:
    BC_EMAIL=your-bc-email@example.com
    BC_PASSWORD=your-bc-password

On first run: logs in, saves cookies to .buildingconnected_cookies.json.
On subsequent runs: reuses saved cookies (re-logins if expired).

Output: bc_current_lead.json with all project fields.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BC_EMAIL = os.getenv("BC_EMAIL", "").strip()
BC_PASSWORD = os.getenv("BC_PASSWORD", "").strip()

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / ".buildingconnected_cookies.json"
OUTPUT_FILE = BASE_DIR / "bc_current_lead.json"

BC_LOGIN_URL = "https://app.buildingconnected.com/login"


def _is_login_page(url: str) -> bool:
    return any(k in url.lower() for k in ("login", "signin", "auth0", "autodesk.com/authenticate"))


async def _load_cookies(context) -> bool:
    """Load saved cookies into the browser context. Returns True if loaded."""
    if not COOKIES_FILE.exists():
        return False
    try:
        cookies = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
        await context.add_cookies(cookies)
        return True
    except Exception as e:
        print(f"[BC] Cookie load failed: {e}", file=sys.stderr)
        return False


async def _save_cookies(context) -> None:
    """Save current browser cookies to file."""
    try:
        cookies = await context.cookies()
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        print(f"[BC] Cookies saved to {COOKIES_FILE.name}")
    except Exception as e:
        print(f"[BC] Cookie save failed: {e}", file=sys.stderr)


async def _do_login(page, headless: bool) -> bool:
    """
    Attempt credential-based login on the BC login page.
    Returns True if login succeeded.
    """
    if not BC_EMAIL or not BC_PASSWORD:
        print("[BC] BC_EMAIL or BC_PASSWORD not set in .env — cannot auto-login.", file=sys.stderr)
        if not headless:
            print("[BC] Browser is open. Please log in manually. Waiting up to 5 minutes...", file=sys.stderr)
            deadline = time.time() + 300
            while time.time() < deadline:
                await page.wait_for_timeout(3000)
                if not _is_login_page(page.url):
                    print("[BC] Manual login detected. Continuing.", file=sys.stderr)
                    return True
            print("[BC] Manual login timeout.", file=sys.stderr)
        return False

    print(f"[BC] Logging in as {BC_EMAIL}...", flush=True)
    await page.goto(BC_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(2000)

    # Try filling email field — BC may use Autodesk Identity or native form
    try:
        # BC login form (confirmed via inspection 2026-02-17):
        # email: #emailField (type=email, name=email)
        # password: #passwordField (type=password, name=password)
        # submit button: text="NEXT"
        # Flow: fill email → fill password → click NEXT
        email_sel = "#emailField, input[type='email'], input[name='email']"
        await page.wait_for_selector(email_sel, timeout=8000)
        await page.fill(email_sel, BC_EMAIL)
        await page.wait_for_timeout(400)

        # Step 2: password (visible on same page for direct BC accounts)
        pw_sel = "#passwordField, input[type='password'], input[name='password']"
        try:
            await page.wait_for_selector(pw_sel, timeout=5000)
            await page.fill(pw_sel, BC_PASSWORD)
            await page.wait_for_timeout(400)
        except Exception:
            # Two-step flow: click Next first to reveal password field
            await page.click("button")
            await page.wait_for_timeout(2000)
            await page.wait_for_selector(pw_sel, timeout=8000)
            await page.fill(pw_sel, BC_PASSWORD)
            await page.wait_for_timeout(400)

        # Step 3: submit — button text is "NEXT" on BC
        submit_sel = "button:has-text('NEXT'), button:has-text('Next'), button[type='submit'], input[type='submit']"
        await page.click(submit_sel)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        if _is_login_page(page.url):
            print("[BC] Login failed — still on login page.", file=sys.stderr)
            return False

        print(f"[BC] Login succeeded. Now at: {page.url}", flush=True)
        return True

    except Exception as e:
        print(f"[BC] Login form error: {e}", file=sys.stderr)
        return False


async def _scrape_project_page(page, url: str) -> dict:
    """
    Navigate to a BC project /info page and extract all available fields.
    Selectors will be refined as we learn the BC DOM structure.
    """
    print(f"[BC] Navigating to project page: {url}", flush=True)
    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
    await page.wait_for_timeout(4000)  # wait for React to render

    # Capture full page text for fallback parsing
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
        "raw_body_text": body_text[:8000],  # for debugging / manual review
    }

    # ── Helper: try multiple selectors, return first match ──────────────────
    async def try_text(*selectors: str, attr: str = None) -> str:
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    return (await el.get_attribute(attr) if attr else await el.inner_text()).strip()
            except Exception:
                continue
        return ""

    # ── Project name ─────────────────────────────────────────────────────────
    data["project_name"] = await try_text(
        "h1", "[data-testid='project-name']", ".project-name", "h2"
    )

    # ── Address ──────────────────────────────────────────────────────────────
    data["project_address"] = await try_text(
        "[data-testid='project-address']",
        "[data-field='address']",
        ".project-address",
        "address",
    )

    # ── GC / Client ───────────────────────────────────────────────────────────
    data["client_name"] = await try_text(
        "[data-testid='company-name']",
        "[data-field='company']",
        ".company-name",
    )
    data["client_short"] = data["client_name"].split(" - ")[0].split(",")[0].strip()

    # ── Bid due date ──────────────────────────────────────────────────────────
    data["bid_due_date"] = await try_text(
        "[data-testid='bid-due']",
        "[data-field='bid-date']",
        ".bid-due-date",
    )

    # ── Project description / scope ───────────────────────────────────────────
    data["scope_description"] = await try_text(
        "[data-testid='project-description']",
        "[data-field='description']",
        ".project-description",
        ".description-text",
        "p",
    )

    # ── Size / sqft ───────────────────────────────────────────────────────────
    data["project_size_sqft"] = await try_text(
        "[data-field='sqft']", "[data-testid='sqft']", ".project-size"
    )

    # ── Contact / attention ───────────────────────────────────────────────────
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

    # ── Fallback: parse body text for common patterns ─────────────────────────
    import re
    if not data["project_address"]:
        m = re.search(r"(\d+\s+\w[\w\s,\.]+(?:NW|NE|SW|SE|Ave|St|Blvd|Rd|Dr)[\w\s,\.]*DC\s*\d{5})", body_text)
        if m:
            data["project_address"] = m.group(1).strip()

    if not data["client_email"]:
        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body_text)
        if m:
            data["client_email"] = m.group(0)

    if not data["bid_due_date"]:
        m = re.search(r"(?:bid|due|deadline)[:\s]*(\w+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})", body_text, re.IGNORECASE)
        if m:
            data["bid_due_date"] = m.group(1).strip()

    return data


async def scrape(url: str, headless: bool = False) -> dict:
    """Main entry: login if needed, then scrape the project page."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        # Try loading saved cookies first
        await _load_cookies(context)
        page = await context.new_page()

        # Navigate to the project URL
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # If redirected to login, do login flow
        if _is_login_page(page.url):
            print("[BC] Not logged in — attempting login...", flush=True)
            ok = await _do_login(page, headless=headless)
            if not ok:
                await browser.close()
                return {"error": "Login failed. Add BC_EMAIL and BC_PASSWORD to .env"}
            # Save fresh cookies
            await _save_cookies(context)
            # Navigate to the target page
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
        else:
            print(f"[BC] Cookie session valid. At: {page.url}", flush=True)
            # Refresh cookies
            await _save_cookies(context)

        data = await _scrape_project_page(page, url)
        await browser.close()
        return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python bc_scrape_project.py <BC_PROJECT_URL>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1].strip()
    headless_flag = "--headless" in sys.argv

    print(f"[BC] Scraping: {url}", flush=True)
    data = asyncio.run(scrape(url, headless=headless_flag))

    if data.get("error"):
        print(f"ERROR: {data['error']}", file=sys.stderr)
        sys.exit(1)

    # Save to bc_current_lead.json
    output = {k: v for k, v in data.items() if k != "raw_body_text"}
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[BC] Saved to {OUTPUT_FILE.name}")
    print(json.dumps(output, indent=2, ensure_ascii=False))

    # Also print raw body for selector debugging
    debug_path = BASE_DIR / "bc_last_page_body.txt"
    debug_path.write_text(data.get("raw_body_text", ""), encoding="utf-8")
    print(f"[BC] Raw page text saved to {debug_path.name} (for selector debugging)")


if __name__ == "__main__":
    main()
