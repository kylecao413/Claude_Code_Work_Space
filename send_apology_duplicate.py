"""
Send short apology for duplicate-proposal delivery (2026-04-22 incident).
GUARDED: will not run if marker file exists — prevents accidental double-send.
"""
import sys
from pathlib import Path
from email_sender import send_from_admin

MARKER = Path(__file__).resolve().parent / ".apology_20260422_sent.marker"

APOLOGIES = [
    {
        "to": "jlopatin@sachse.net",
        "subject": "Apologies — duplicate proposal delivery (Neko Health)",
        "body": """Hi Jonathan,

Apologies — a send-script hiccup on our end delivered our Neko Health proposal to you twice. Please disregard the duplicate; either copy is our single current offer.

Thanks for your patience.
""",
    },
    {
        "to": "natasha.solis@desbuild.com",
        "subject": "Apologies — duplicate proposal delivery (B94 Breaker Repair)",
        "body": """Hi Natasha,

Apologies — a send-script hiccup on our end delivered our B94 Breaker Repair proposal to you twice. Please disregard the duplicate; either copy is our single current offer.

Thanks for your patience.
""",
    },
]

def main():
    if "--dry-run" in sys.argv:
        for em in APOLOGIES:
            print(f"\n=== TO: {em['to']} ===")
            print(f"Subject: {em['subject']}")
            print(f"Body:\n{em['body']}")
        print("[DRY RUN]")
        return
    if MARKER.exists():
        print(f"[GUARD] apologies already sent (marker: {MARKER.name}). Refusing to re-send.")
        print(f"[GUARD] delete the marker file manually if you really need to re-send.")
        sys.exit(1)
    for em in APOLOGIES:
        ok, msg = send_from_admin(em["to"], em["subject"], em["body"])
        print(f"{'SENT' if ok else 'FAIL'} → {em['to']}: {msg}")
    MARKER.write_text("sent 2026-04-22")
    print(f"[marker written: {MARKER.name}]")

if __name__ == "__main__":
    main()
