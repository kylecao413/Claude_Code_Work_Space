"""
handoff_to_telegram.py - 将项目交接报告推送到用户的 Telegram。
用法: python core_tools/handoff_to_telegram.py
需要 .env 中配置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_ALLOWED_CHAT_IDS。
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# ALLOWED_CHAT_IDS 是逗号分隔的，取第一个作为推送目标
CHAT_IDS_RAW = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()

if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env", file=sys.stderr)
    sys.exit(1)
if not CHAT_IDS_RAW:
    print("Error: TELEGRAM_ALLOWED_CHAT_IDS not found in .env", file=sys.stderr)
    sys.exit(1)

CHAT_ID = CHAT_IDS_RAW.split(",")[0].strip()


def send_message(text, chat_id=CHAT_ID):
    """Send a message via Telegram Bot API. Splits if over 4096 chars."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [text[i:i + 4096] for i in range(0, len(text), 4096)]
    for chunk in chunks:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
        }, timeout=15)
        if not resp.ok:
            print(f"Telegram API error: {resp.status_code} {resp.text}", file=sys.stderr)
            return False
    return True


def build_handoff_summary():
    from datetime import datetime
    return f"""🚀 *BCC Automation - Handoff Report*
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
🤖 From: Claude Code (Desktop) → Mobile Command (Telegram)

✅ *Completed Today:*
1. *Architecture:* Established Centaur Architecture (Claude = Hands, Gemini = Brain).
2. *Tools:* Created `core_tools/ask_senior.py` — bridge to Gemini 2.5 Pro for code review.
3. *Upgrade:* Verified API Key is Tier 1 (Paid). Model set to `gemini-2.5-pro`, fallback `--model gemini-2.5-flash`.
4. *Rules:* Created `CLAUDE.md` enforcing Draft → Review (ask\\_senior) → Fix workflow.
5. *Validation:* `ask_senior.py` passed 3 rounds of self-review. Fixed: path traversal (is\\_relative\\_to), error handling (prompt\\_feedback), API usage (generate\\_content).

🚧 *Next Actions:*
- Review proposal for St. Joseph's Phase I
- Check if `buildingconnected_bid_scraper.py` needs a run
- Brainstorm Plan Review marketing emails via Gemini Bot

💡 *Note:*
Each new Claude Code session starts fresh. Paste relevant context or reference `CLAUDE.md` / `BCC_PROPOSAL_RULES.md` for continuity.
"""


if __name__ == "__main__":
    summary = build_handoff_summary()
    print("Sending handoff report to Telegram...", file=sys.stderr)
    ok = send_message(summary)
    if ok:
        print("Handoff report sent successfully.", file=sys.stderr)
    else:
        sys.exit(1)
