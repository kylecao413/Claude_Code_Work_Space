"""
Read .google_cookies.json and show when cookies expire. Google controls expiry; we cannot extend it.
Run with --check: exit 0 if cookie exists and not expired, 1 if missing/expired (for agent to trigger re-login).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

COOKIES_PATH = Path(__file__).resolve().parent / ".google_cookies.json"

# Buffer: treat as expired this many minutes before actual expiry so we refresh in time
EXPIRY_BUFFER_MINUTES = 60

def is_cookie_valid() -> bool:
    """True if .google_cookies.json exists and soonest expiry is in the future (with buffer)."""
    if not COOKIES_PATH.exists():
        return False
    try:
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    cookies = data.get("cookies", [])
    if not cookies:
        return False
    now = datetime.now(timezone.utc)
    soonest_sec = None
    for c in cookies:
        exp = c.get("expires", -1)
        if exp == -1:
            continue
        try:
            soonest_sec = min(exp, soonest_sec) if soonest_sec is not None else exp
        except Exception:
            pass
    if soonest_sec is None:
        return True  # only session cookies; assume valid
    cutoff = now.timestamp() + EXPIRY_BUFFER_MINUTES * 60
    return soonest_sec > cutoff


def main():
    if not COOKIES_PATH.exists():
        print("No .google_cookies.json found. Cookie was not saved.")
        print("To save: 1) Close all Chrome 2) start_chrome_for_gemini_login.bat 3) Log in at gemini.google.com in THAT window 4) python google_gemini_login_chrome.py")
        return
    with open(COOKIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies", [])
    if not cookies:
        print("Cookie file exists but has no cookies.")
        return
    now = datetime.utcnow()
    expiries = []
    for c in cookies:
        exp = c.get("expires", -1)
        if exp == -1:
            expiries.append((c.get("name", "?"), "session (expires when browser closes)"))
        else:
            try:
                dt = datetime.utcfromtimestamp(exp)
                expiries.append((c.get("name", "?"), dt.strftime("%Y-%m-%d %H:%M UTC")))
            except Exception:
                expiries.append((c.get("name", "?"), str(exp)))
    # Show soonest expiry (most relevant for "when will login break")
    with_dates = [(n, e) for n, e in expiries if "session" not in e and "UTC" in e]
    if with_dates:
        from datetime import timezone
        dates = []
        for n, e in with_dates:
            try:
                d = datetime.strptime(e.replace(" UTC", ""), "%Y-%m-%d %H:%M")
                dates.append((n, d))
            except Exception:
                pass
        if dates:
            soonest = min(dates, key=lambda x: x[1])
            print(f"Cookie file: {COOKIES_PATH}")
            print(f"Total cookies: {len(cookies)}")
            print(f"Soonest expiry (key cookie): {soonest[0]} -> {soonest[1].strftime('%Y-%m-%d %H:%M')} UTC")
            print("When that passes, you'll need to re-run the fresh login (start_chrome_for_gemini_login.bat -> log in -> google_gemini_login_chrome.py).")
    else:
        print(f"Cookie file: {COOKIES_PATH}")
        print(f"Total cookies: {len(cookies)} (session or no expiry info)")
        print("Session cookies expire when the browser is closed. For long-lived use, ensure you logged in with 'Remember me' in the Chrome started by start_chrome_for_gemini_login.bat, then saved with google_gemini_login_chrome.py.")
    return

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # For agent: exit 0 = valid, 1 = expired/missing (trigger re-login)
        sys.exit(0 if is_cookie_valid() else 1)
    main()
