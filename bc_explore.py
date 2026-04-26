"""
bc_explore.py — Diagnostic script to explore BC page structure.
Logs in (using saved cookies), navigates to multiple BC pages,
takes screenshots, and dumps all links and clickable elements.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / ".buildingconnected_cookies.json"


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

        # Check if cookies are still valid
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        if _is_login_page(page.url):
            print("NOT LOGGED IN. Run bc_batch_scrape.py first to login and save cookies.")
            await browser.close()
            return

        print(f"Logged in. At: {page.url}")

        # Explore different pages
        pages_to_check = [
            "/bids",
            "/bids/invites",
            "/bids/invited",
            "/bids/open",
            "/bids/pending",
            "/bids/active",
            "/subcontractor/bids",
            "/opportunities",
        ]

        for path in pages_to_check:
            url = f"https://app.buildingconnected.com{path}"
            print(f"\n{'='*60}")
            print(f"Checking: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(4000)
                final_url = page.url
                print(f"  Final URL: {final_url}")

                if _is_login_page(final_url):
                    print("  → Redirected to login")
                    continue

                safe_name = path.replace("/", "_").strip("_") or "root"
                await page.screenshot(path=str(BASE_DIR / f"bc_explore_{safe_name}.png"), full_page=True)

                # Get ALL links on the page
                all_links = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('a[href]'))
                        .map(a => ({href: a.href, text: a.innerText.trim().slice(0, 120)}))
                        .filter(a => a.text.length > 0)
                """)
                print(f"  All links: {len(all_links)}")
                for link in all_links[:15]:
                    print(f"    {link['text'][:50]:50s} → {link['href'][:80]}")

                # Get page body text snippet
                body = await page.inner_text("body")
                print(f"  Body preview ({len(body)} chars): {body[:500]}")

                # Look for any table rows, cards, or list items
                row_counts = await page.evaluate("""
                    () => ({
                        tableRows: document.querySelectorAll('table tbody tr').length,
                        cards: document.querySelectorAll('[class*="card"], [class*="Card"]').length,
                        listItems: document.querySelectorAll('li').length,
                        divRows: document.querySelectorAll('[class*="row"], [class*="Row"]').length,
                        buttons: document.querySelectorAll('button').length,
                        allClickable: document.querySelectorAll('[role="button"], [onclick], [data-testid]').length,
                    })
                """)
                print(f"  Elements: {json.dumps(row_counts)}")

            except Exception as e:
                print(f"  Error: {e}")

        # Also check the sidebar navigation
        print(f"\n{'='*60}")
        print("Checking sidebar navigation...")
        await page.goto("https://app.buildingconnected.com/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)

        # Find all nav/sidebar links
        nav_links = await page.evaluate("""
            () => {
                const nav = document.querySelectorAll('nav a, [class*="sidebar"] a, [class*="Sidebar"] a, [class*="nav"] a, [role="navigation"] a');
                return Array.from(nav).map(a => ({href: a.href, text: a.innerText.trim().slice(0, 80), ariaLabel: a.getAttribute('aria-label') || ''}));
            }
        """)
        print(f"Nav links: {len(nav_links)}")
        for link in nav_links:
            print(f"  {link.get('ariaLabel', '') or link['text']:40s} → {link['href'][:80]}")

        # Also check all left-side icon links
        sidebar_icons = await page.evaluate("""
            () => {
                // Check all elements in the first 100px from the left (sidebar area)
                const all = Array.from(document.querySelectorAll('a, button, [role="link"], [role="button"]'));
                return all
                    .filter(el => el.getBoundingClientRect().left < 60)
                    .map(el => ({
                        tag: el.tagName,
                        href: el.href || '',
                        text: el.innerText.trim().slice(0, 50),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        title: el.getAttribute('title') || '',
                        rect: {x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y}
                    }));
            }
        """)
        print(f"\nSidebar elements (left < 60px): {len(sidebar_icons)}")
        for el in sidebar_icons:
            label = el.get('ariaLabel') or el.get('title') or el.get('text') or '(no label)'
            print(f"  [{el['tag']}] {label:40s} → {el.get('href', '')[:60]}  (y={el['rect']['y']:.0f})")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
