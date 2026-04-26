"""Read PrivateEmail (admin@ / ycao@) inboxes via IMAP.

Usage:
    python core_tools/privmail_reader.py --account ycao --search "harkins" --days 30
    python core_tools/privmail_reader.py --account admin --unread
    python core_tools/privmail_reader.py --account ycao --from "prequal@harkinsbuilders.com"
"""
from __future__ import annotations

import argparse
import email
import imaplib
import os
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

IMAP_HOST = os.getenv("PRIV_MAIL_IMAP_HOST", "mail.privateemail.com")
IMAP_PORT = int(os.getenv("PRIV_MAIL_IMAP_PORT", "993"))

ACCOUNTS = {
    "admin": ("PRIV_MAIL1_USER", "PRIV_MAIL1_PASS"),
    "ycao": ("PRIV_MAIL2_USER", "PRIV_MAIL2_PASS"),
}


def _decode(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def fetch(account: str, *, search: str | None, sender: str | None, days: int, unread: bool, limit: int) -> None:
    user_key, pass_key = ACCOUNTS[account]
    user = os.getenv(user_key)
    password = os.getenv(pass_key)
    if not user or not password:
        raise SystemExit(f"Missing {user_key}/{pass_key} in .env")

    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(user, password)
    imap.select("INBOX")

    criteria: list[str] = []
    if unread:
        criteria.append("UNSEEN")
    if sender:
        criteria += ["FROM", f'"{sender}"']
    if search:
        criteria += ["TEXT", f'"{search}"']
    if days:
        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        criteria += ["SINCE", since]
    if not criteria:
        criteria = ["ALL"]

    status, data = imap.search(None, *criteria)
    if status != "OK":
        raise SystemExit(f"IMAP search failed: {status}")

    ids = data[0].split()
    if not ids:
        print(f"[{account}] no matches.")
        return

    ids = ids[-limit:][::-1]
    print(f"[{account}] {len(ids)} message(s) (newest first):\n")
    for mid in ids:
        status, msg_data = imap.fetch(mid, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        print(f"--- ID {mid.decode()} ---")
        print(f"From:    {_decode(msg.get('From'))}")
        print(f"To:      {_decode(msg.get('To'))}")
        print(f"Date:    {_decode(msg.get('Date'))}")
        print(f"Subject: {_decode(msg.get('Subject'))}")
        body = _body(msg).strip()
        if len(body) > 4000:
            body = body[:4000] + "\n...[truncated]..."
        print(body)
        print()

    imap.logout()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--account", choices=list(ACCOUNTS), required=True)
    p.add_argument("--search", help="Full-text substring")
    p.add_argument("--from", dest="sender", help="Sender substring")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--unread", action="store_true")
    p.add_argument("--limit", type=int, default=10)
    args = p.parse_args()
    fetch(args.account, search=args.search, sender=args.sender, days=args.days, unread=args.unread, limit=args.limit)


if __name__ == "__main__":
    main()
