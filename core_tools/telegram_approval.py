"""
telegram_approval.py — Synchronous Telegram approval loop for BCC proposals.

Sends a .md proposal draft to Telegram, long-polls for the user's reply,
parses changes (price, visits, description), and returns the approval result.

Zero AI cost — uses Telegram Bot API (requests) only.

Usage (standalone):
    python core_tools/telegram_approval.py --md Pending_Approval/Outbound/Proposal_Draft_XYZ.md

NOTE: Do NOT run this simultaneously with telegram_bot.py (both consume getUpdates).
      Stop telegram_bot.py before calling this script, or use it from proposal_generator.py
      which calls it inline before starting the bot.
"""
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    _dir = Path(__file__).resolve().parent.parent
    load_dotenv(_dir / ".env")
except ImportError:
    pass

import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_IDS_RAW = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
CHAT_ID = CHAT_IDS_RAW.split(",")[0].strip() if CHAT_IDS_RAW else ""
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _check_config() -> None:
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_CHAT_IDS not set in .env"
        )


def send_message(text: str, parse_mode: str = None) -> int | None:
    """Send a message (split if > 4000 chars). Returns last message_id or None."""
    _check_config()
    if not text:
        return None
    chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
    last_id = None
    for chunk in chunks:
        payload = {"chat_id": CHAT_ID, "text": chunk}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            resp = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
            if resp.ok:
                last_id = resp.json().get("result", {}).get("message_id")
            else:
                print(
                    f"[Telegram] send failed: {resp.status_code} {resp.text[:200]}",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"[Telegram] send error: {e}", file=sys.stderr)
    return last_id


def _get_updates(offset: int = None, timeout: int = 30) -> list:
    """Long-poll Telegram for new updates."""
    params = {"timeout": timeout, "limit": 10, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        resp = requests.get(
            f"{API_BASE}/getUpdates", params=params, timeout=timeout + 10
        )
        if resp.ok:
            return resp.json().get("result", [])
    except requests.exceptions.Timeout:
        pass
    except Exception as e:
        print(f"[Telegram] getUpdates error: {e}", file=sys.stderr)
    return []


def _get_current_offset() -> int | None:
    """Get next update_id to skip any already-queued messages."""
    updates = _get_updates(timeout=2)
    if updates:
        return max(u["update_id"] for u in updates) + 1
    return None


def parse_reply(text: str) -> dict:
    """
    Parse user Telegram reply into a structured change/approval dict.

    Returns:
        {
          "approved": bool,      # True if approval keyword detected
          "price": int | None,   # New $/visit if specified
          "visits": int | None,  # New visit count if specified
          "description": str | None,  # Description override if specified
          "note": str,           # Raw note/comment from user
          "raw": str,            # Original message text
        }
    """
    t = (text or "").strip()
    t_low = t.lower()

    result: dict = {
        "approved": False,
        "price": None,
        "visits": None,
        "description": None,
        "note": "",
        "raw": t,
    }

    # Approval keywords (English + Chinese)
    APPROVE = {
        "ok", "okay", "approve", "approved", "yes", "generate", "good",
        "looks good", "send", "lgtm", "go ahead",
        "同意", "确认", "好", "可以", "生成", "发送", "没问题",
    }
    if any(kw in t_low for kw in APPROVE):
        result["approved"] = True

    # Price change: "price 350", "$350", "350/visit", "fee 375", "325每次"
    price_m = (
        re.search(r"(?:price|fee|rate|单价)[:\s]*\$?(\d{3,4})", t_low)
        or re.search(r"\$(\d{3,4})", t)
        or re.search(r"(\d{3,4})\s*(?:/visit|per visit|每次|每visit)", t_low)
    )
    if price_m:
        val = int(price_m.group(1))
        if 100 <= val <= 2000:  # sanity: $/visit range
            result["price"] = val

    # Visit count: "6 visits", "visits: 4", "4次", "改成5次"
    visits_m = (
        re.search(r"(\d+)\s*(?:visits?|times?|次|inspections?)", t_low)
        or re.search(r"visit[s\s]*[:\s]+(\d+)", t_low)
    )
    if visits_m:
        val = int(visits_m.group(1))
        if 1 <= val <= 100:
            result["visits"] = val

    # Description override: "description: ..." or "desc: ..." or "scope: ..."
    desc_m = re.search(
        r"(?:description|desc|scope|项目描述)[:\s]+(.+)", t, re.IGNORECASE | re.DOTALL
    )
    if desc_m:
        result["description"] = desc_m.group(1).strip()

    # Anything else: treat as a free-form note to attach to the proposal
    if not result["approved"] and not any(
        [result["price"], result["visits"], result["description"]]
    ):
        result["note"] = t

    return result


def send_proposal_for_review(
    md_path: str | Path, project: dict, price: int, visits: int
) -> bool:
    """
    Send proposal .md draft to the configured Telegram chat for review.
    Returns True if sent successfully.
    """
    md_path = Path(md_path)
    if not md_path.exists():
        print(f"[Telegram] .md file not found: {md_path}", file=sys.stderr)
        return False

    md_content = md_path.read_text(encoding="utf-8")
    total = price * visits

    header = (
        "📋 *Proposal Draft — Review Required*\n"
        f"📁 `{md_path.name}`\n"
        f"🗓 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"*Project:* {project.get('name', 'N/A')}\n"
        f"*Client:* {project.get('client', 'N/A')}\n"
        f"*Contact:* {project.get('attention', project.get('contact_name', 'N/A'))}\n"
        f"*Address:* {project.get('address', 'N/A')}\n\n"
        f"💰 *Fee:* ${price}/visit × {visits} visits = *${total}*\n\n"
        "─────────────────────\n"
        "Reply with:\n"
        "• `OK` — approve & generate Word doc + PDF\n"
        "• `price 350` — change $/visit\n"
        "• `visits 6` — change visit count\n"
        "• `description: [text]` — override project description\n"
        "• Any text — add a note / request adjustment\n"
        "─────────────────────\n"
        "_Full draft below ↓_"
    )

    # Send header with Markdown formatting
    send_message(header, parse_mode="Markdown")
    # Send .md content as plain text (no parse_mode — avoids markdown parse errors)
    send_message(md_content)
    return True


def wait_for_approval(timeout_minutes: int = 120) -> dict | None:
    """
    Block and wait for a Telegram reply. Returns parsed reply dict or None on timeout.

    Args:
        timeout_minutes: How long to wait before giving up (default 2 hours).
    """
    _check_config()
    deadline = time.time() + timeout_minutes * 60

    # Skip any messages already in the queue before we started waiting
    offset = _get_current_offset()

    mins = timeout_minutes
    print(
        f"[Telegram] Waiting for approval (timeout: {mins} min). "
        "Reply OK or send changes on Telegram.",
        flush=True,
    )

    while time.time() < deadline:
        remaining = int(deadline - time.time())
        if remaining <= 0:
            break
        poll_secs = min(30, remaining)
        updates = _get_updates(offset=offset, timeout=poll_secs)
        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message", {})
            if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID):
                continue  # ignore messages from other chats
            text = (msg.get("text") or "").strip()
            if not text or text.startswith("/"):
                continue  # ignore bot commands
            print(f"[Telegram] Received reply: {text[:100]}", flush=True)
            return parse_reply(text)

    print("[Telegram] Timeout — no reply received.", flush=True)
    return None


def run_telegram_approval_loop(
    md_path: str | Path,
    project: dict,
    price: int,
    visits: int,
    max_rounds: int = 3,
    timeout_per_round: int = 120,
) -> tuple[bool, dict, int, int]:
    """
    Full interactive approval loop:
      1. Send proposal .md to Telegram
      2. Wait for reply
      3. Apply any changes (price / visits / description / note)
      4. If not yet approved, repeat (up to max_rounds)

    Returns:
        (approved: bool, updated_project: dict, final_price: int, final_visits: int)
    """
    project = dict(project)  # don't mutate caller's dict

    for round_num in range(1, max_rounds + 1):
        print(f"[Telegram] Review round {round_num}/{max_rounds}", flush=True)
        send_proposal_for_review(md_path, project, price, visits)

        reply = wait_for_approval(timeout_minutes=timeout_per_round)

        if reply is None:
            send_message(
                f"⏰ No reply received after {timeout_per_round} min. "
                "Proposal saved — run again or approve the .md manually."
            )
            return False, project, price, visits

        # Apply changes
        changes = []
        if reply.get("price"):
            price = reply["price"]
            changes.append(f"price → ${price}/visit")
        if reply.get("visits"):
            visits = reply["visits"]
            changes.append(f"visits → {visits}")
        if reply.get("description"):
            project["description"] = reply["description"]
            changes.append("description updated")
        if reply.get("note"):
            project.setdefault("_notes", [])
            project["_notes"].append(reply["note"])
            changes.append(f"note logged: {reply['note'][:60]}")

        if changes:
            total = price * visits
            send_message(
                f"✏️ Applied: {', '.join(changes)}\n"
                f"New total: ${price} × {visits} = ${total}\n\n"
                "Reply `OK` to approve or send more changes."
            )

        if reply.get("approved"):
            send_message(
                f"✅ Approved! Generating Word doc...\n"
                f"Fee: ${price}/visit × {visits} visits = ${price * visits}"
            )
            return True, project, price, visits

    # Exhausted rounds without approval
    send_message(
        f"⛔ {max_rounds} rounds reached without approval. "
        "Proposal on hold — approve the .md file manually."
    )
    return False, project, price, visits


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Send a proposal .md to Telegram and wait for approval."
    )
    ap.add_argument("--md", required=True, help="Path to the proposal .md draft file")
    ap.add_argument("--price", type=int, default=325, help="Price per visit (default 325)")
    ap.add_argument("--visits", type=int, default=4, help="Estimated visits (default 4)")
    ap.add_argument("--timeout", type=int, default=120, help="Timeout per round in minutes")
    args = ap.parse_args()

    # Minimal project dict for standalone usage
    project = {"name": Path(args.md).stem, "client": "", "address": ""}
    approved, proj, price, visits = run_telegram_approval_loop(
        args.md, project, args.price, args.visits,
        max_rounds=3, timeout_per_round=args.timeout
    )
    if approved:
        print(f"Approved: ${price}/visit × {visits} = ${price * visits}")
        sys.exit(0)
    else:
        print("Not approved — proposal on hold.", file=sys.stderr)
        sys.exit(1)
