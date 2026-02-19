"""
Telegram bot for BCC Sales Automation.
Commands: pipeline status, follow-up management, draft approvals, daily briefing, Gemini chat.
Requires in .env: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_CHAT_IDS; free-text chat needs GEMINI_API_KEY.
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
_env_pending = os.environ.get("PENDING_APPROVAL_DIR", "").strip().strip('"')
PENDING_DIR = Path(_env_pending) if _env_pending else BASE_DIR / "Pending_Approval"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"')
MAX_TELEGRAM_MESSAGE = 4000


def get_pending_drafts():
    """返回待审批草稿列表（不含 -OK）。"""
    if not PENDING_DIR.exists():
        return []
    out = []
    for f in PENDING_DIR.rglob("*.md"):
        if f.is_file() and "-OK" not in f.name and "README" not in f.name:
            rel = f.relative_to(PENDING_DIR)
            out.append((str(rel), f))
    return out


def get_summary_text():
    """今日进度摘要文本。"""
    from datetime import datetime
    drafts = get_pending_drafts()
    sent_dir = BASE_DIR / "Sent"
    sent_today = 0
    if sent_dir.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        for f in sent_dir.glob("*.md"):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d") == today:
                    sent_today += 1
            except Exception:
                pass
    lines = [
        f"📊 BCC 今日简报 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"待审批草稿: {len(drafts)}",
        f"今日已发送: {sent_today}",
        "",
        "待审批列表:",
    ]
    for name, _ in drafts[:15]:
        lines.append(f"  • {name}")
    if len(drafts) > 15:
        lines.append(f"  … 共 {len(drafts)} 个")
    return "\n".join(lines)


def get_agent_context() -> str:
    """供 AI 参考的当前业务上下文（待审批、已发、Research 等）。"""
    from datetime import datetime
    drafts = get_pending_drafts()
    sent_dir = BASE_DIR / "Sent"
    sent_today = 0
    if sent_dir.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        for f in sent_dir.glob("*.md"):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d") == today:
                    sent_today += 1
            except Exception:
                pass
    research = list(BASE_DIR.glob("Research_*.md"))
    research_names = [f.stem.replace("Research_", "") for f in research[:20]]
    return (
        f"Today: {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
        f"Pending approval drafts: {len(drafts)}. Sent today: {sent_today}. "
        f"Draft names: {[n for n, _ in drafts[:15]]}. "
        f"Research files (companies): {research_names}."
    )


def call_gemini_agent(user_message: str, context: str) -> str:
    """同步调用 Gemini API（新 SDK google-genai），返回模型回复（用于 BCC 销售助理）。"""
    if not GEMINI_API_KEY:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""You are the AI assistant for Building Code Consulting (BCC). Yue Cao (PE, MCP) uses you via Telegram for lead gen and CRM.

Current context: {context}

The user just said (via Telegram): {user_message}

Reply in a helpful, concise way. You can answer questions about pending drafts, sent emails, research, or suggest next steps (e.g. run batch research, approve a draft). Keep the reply under 500 words and in the same language as the user when possible."""
        for model_id in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-001"):
            try:
                response = client.models.generate_content(model=model_id, contents=prompt)
                if response and getattr(response, "text", None):
                    return response.text.strip()
            except Exception as e:
                err = str(e).lower()
                if "404" in err or "not found" in err:
                    continue
                return f"Agent 调用出错: {e}"
    except Exception as e:
        return f"Agent 调用出错: {e}"
    return "Agent 调用出错: 当前 API 下无可用模型，请检查 Google AI Studio 可用模型列表。"



def get_pipeline_status() -> str:
    """Read pipeline_checkpoint.json and return a status summary."""
    cp_path = BASE_DIR / "pipeline_checkpoint.json"
    if not cp_path.exists():
        # Check if drafts are ready instead
        drafts = list((BASE_DIR / "Pending_Approval" / "Outbound").glob("CW_*.md"))
        if drafts:
            return (f"📋 No active pipeline run.\n"
                    f"But {len(drafts)} CW draft(s) are ready in Outbound/.\n"
                    f"Send with: python send_cw_outreach.py --all")
        return "📋 No active pipeline run. No checkpoint found."
    try:
        import json as _json
        cp = _json.loads(cp_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Error reading checkpoint: {e}"

    phase_names = ["scrape leads", "research companies", "compile report",
                   "send report to Telegram", "generate emails", "save drafts", "send drafts to Telegram"]
    phase_keys  = ["phase1_done", "phase2_done", "phase3_done",
                   "phase4_done", "phase5_done", "phase6_done", "phase7_done"]
    lines = [f"🔄 Pipeline Checkpoint ({cp.get('last_updated', '?')[:16]}):"]
    for i, (name, key) in enumerate(zip(phase_names, phase_keys), 1):
        icon = "✅" if cp.get(key) else "⏳"
        lines.append(f"  {icon} Phase {i}: {name}")
    if cp.get("phase2_researched"):
        lines.append(f"  (Phase 2 partial: {len(cp['phase2_researched'])} companies done)")
    next_phase = next((i + 1 for i, k in enumerate(phase_keys) if not cp.get(k)), 8)
    if next_phase <= 7:
        lines.append(f"\nResume with: python run_cw_leads_pipeline.py --resume")
    else:
        lines.append("\nAll phases complete.")
    return "\n".join(lines)


def get_followup_due(days: int = 4) -> list[dict]:
    """Return contacts due for follow-up."""
    import csv as _csv
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    log_path = BASE_DIR / "sent_log.csv"
    if not log_path.exists():
        return []
    cutoff = _dt.now(_tz.utc) - _td(days=days)
    due = []
    with open(log_path, newline="", encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            if row.get("replied", "").strip() in ("1", "true", "yes"):
                continue
            if row.get("followup_sent_at", "").strip():
                continue
            ts_str = row.get("sent_at", "")
            try:
                ts = _dt.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_tz.utc)
            except Exception:
                continue
            if ts <= cutoff:
                due.append(row)
    return due


def mark_contact_replied(email: str) -> tuple[int, str]:
    """Mark a contact as replied in sent_log.csv. Returns (count, message)."""
    import csv as _csv
    log_path = BASE_DIR / "sent_log.csv"
    if not log_path.exists():
        return 0, "sent_log.csv not found."
    rows = []
    fieldnames = None
    count = 0
    with open(log_path, newline="", encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if row.get("contact_email", "").strip().lower() == email.strip().lower():
                row["replied"] = "1"
                count += 1
            rows.append(row)
    if count == 0:
        return 0, f"No contact found with email: {email}"
    # Ensure new columns present
    for col in ("replied", "followup_sent_at"):
        if col not in fieldnames:
            fieldnames = list(fieldnames) + [col]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return count, f"✅ Marked {count} row(s) as replied for {email}"


def approve_and_send(base_name: str) -> str:
    """
    将指定草稿“审批”：在 Outbound/Replies 下查找匹配的 .md，复制为 -OK.md 后调用 approval_monitor 处理。
    base_name 可为文件名（不含 -OK.md）或公司名。发送成功后 -OK 文件会移至 Sent/。
    """
    from approval_monitor import process_approved_file
    if not PENDING_DIR.exists():
        return "无 Pending_Approval 目录。"
    base_name = base_name.strip().replace("-OK", "").replace(".md", "")
    for f in PENDING_DIR.rglob("*.md"):
        if not f.is_file() or "-OK" in f.name or "README" in f.name:
            continue
        if base_name.lower() in f.stem.lower() or f.stem.lower() in base_name.lower():
            ok_path = f.parent / f"{f.stem}-OK.md"
            if ok_path.exists():
                ok_path.unlink()
            import shutil
            shutil.copy2(f, ok_path)
            if process_approved_file(ok_path):
                return f"✅ 已发送: {f.name}"
            if ok_path.exists():
                ok_path.unlink()
            return "❌ 发送失败，请检查草稿中**邮箱**、主题、正文是否已填写。"
    return f"未找到匹配草稿: {base_name}"


def run_polling():
    """使用 python-telegram-bot 轮询（需 pip install python-telegram-bot）。"""
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
    except ImportError:
        print("请安装: pip install python-telegram-bot")
        sys.exit(1)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
    if not token:
        print("请在 .env 中配置 TELEGRAM_BOT_TOKEN（从 @BotFather 获取）。")
        sys.exit(1)

    allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    allowed_ids = set()
    for x in allowed.replace(",", " ").split():
        try:
            allowed_ids.add(int(x.strip()))
        except ValueError:
            pass

    def _auth(chat_id) -> bool:
        return not allowed_ids or (chat_id and chat_id in allowed_ids)

    async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        drafts = get_pending_drafts()
        if not drafts:
            await update.message.reply_text("暂无待审批草稿。")
            return
        lines = [f"📋 待审批 ({len(drafts)}):"] + [f"• {n}" for n, _ in drafts[:20]]
        if len(drafts) > 20:
            lines.append(f"… 共 {len(drafts)} 个")
        await update.message.reply_text("\n".join(lines))

    async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        await update.message.reply_text(get_summary_text())

    async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        name = " ".join(context.args) if context.args else ""
        if not name:
            await update.message.reply_text("用法: /approve <草稿名或公司名>")
            return
        msg = approve_and_send(name)
        await update.message.reply_text(msg)

    async def cmd_pipeline_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        loop = asyncio.get_event_loop()
        msg = await loop.run_in_executor(None, get_pipeline_status)
        await update.message.reply_text(msg)

    async def cmd_followup_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        loop = asyncio.get_event_loop()
        due = await loop.run_in_executor(None, get_followup_due)
        if not due:
            await update.message.reply_text("✅ No follow-ups due. Everyone has replied or is still within the 4-day window.")
            return
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        lines = [f"📬 {len(due)} contact(s) due for follow-up:\n"]
        now = _dt.now(_tz.utc)
        for row in due[:20]:
            try:
                ts = _dt.fromisoformat(row.get("sent_at", "").replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_tz.utc)
                age = (now - ts).days
            except Exception:
                age = "?"
            lines.append(f"• {row.get('contact_name', '?')} ({row.get('company', '?')}) — {age}d ago")
        if len(due) > 20:
            lines.append(f"... and {len(due) - 20} more")
        lines.append("\nTo send follow-ups: /followup_send\nTo mark someone replied: /mark_replied <email>")
        await update.message.reply_text("\n".join(lines))

    _pending_followup_send: dict[int, bool] = {}

    async def cmd_followup_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        chat_id = update.effective_chat.id if update.effective_chat else 0
        loop = asyncio.get_event_loop()
        due = await loop.run_in_executor(None, get_followup_due)
        if not due:
            await update.message.reply_text("No follow-ups due right now.")
            return

        # Two-step: first call shows list + asks confirmation, second call (within 60s) sends
        if not _pending_followup_send.get(chat_id):
            _pending_followup_send[chat_id] = True
            lines = [f"⚠️ About to send {len(due)} follow-up email(s) from admin@buildingcodeconsulting.com:\n"]
            for row in due[:15]:
                lines.append(f"• {row.get('contact_name', '?')} <{row.get('contact_email', '?')}>")
            if len(due) > 15:
                lines.append(f"... and {len(due) - 15} more")
            lines.append("\nRun /followup_send again within 60 seconds to confirm and send.")
            await update.message.reply_text("\n".join(lines))
            # Auto-reset after 60 seconds
            async def _reset():
                await asyncio.sleep(60)
                _pending_followup_send.pop(chat_id, None)
            asyncio.create_task(_reset())
        else:
            _pending_followup_send.pop(chat_id, None)
            await update.message.reply_text(f"📤 Sending {len(due)} follow-up(s)...")
            from email_sender import send_from_admin
            from datetime import datetime as _dt, timezone as _tz
            import csv as _csv
            sent_count = 0
            log_path = BASE_DIR / "sent_log.csv"
            rows_all = []
            fieldnames = None
            with open(log_path, newline="", encoding="utf-8") as f:
                reader = _csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows_all = list(reader)
            for col in ("replied", "followup_sent_at"):
                if col not in fieldnames:
                    fieldnames.append(col)
            sent_emails = {r.get("contact_email", "").lower() for r in due}
            for row in rows_all:
                if row.get("contact_email", "").lower() not in sent_emails:
                    continue
                if row.get("followup_sent_at", "").strip():
                    continue
                name = row.get("contact_name", "")
                first = name.split()[0] if name else "there"
                project = row.get("project", "") or row.get("subject", "")
                body = (f"Hi {first},\n\nI wanted to follow up on my earlier message"
                        + (f" regarding {project}" if project else "")
                        + ". I understand you're busy — just wanted to make sure this didn't get lost.\n\n"
                        "If you have any questions or would like to set up a quick call, "
                        "I'm happy to make time. Looking forward to connecting.")
                ok, _ = await loop.run_in_executor(
                    None, lambda r=row, b=body: send_from_admin(r["contact_email"], f"Re: {r.get('subject', '')}", b)
                )
                if ok:
                    row["followup_sent_at"] = _dt.now(_tz.utc).isoformat()
                    sent_count += 1
            with open(log_path, "w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows_all)
            await update.message.reply_text(f"✅ Sent {sent_count}/{len(due)} follow-up(s). sent_log updated.")

    _pending_send_batch: dict[int, list] = {}

    async def cmd_send_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send top N CW drafts from Outbound/. Two-step confirm."""
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        chat_id = update.effective_chat.id if update.effective_chat else 0
        try:
            n = int(context.args[0]) if context.args else 10
        except (ValueError, IndexError):
            n = 10
        outbound = BASE_DIR / "Pending_Approval" / "Outbound"
        drafts = sorted(outbound.glob("CW_*.md"))[:n]
        if not drafts:
            await update.message.reply_text("No CW drafts found in Outbound/. Run the pipeline first.")
            return
        if not _pending_send_batch.get(chat_id):
            _pending_send_batch[chat_id] = drafts
            lines = [f"⚠️ About to send {len(drafts)} draft(s) from admin@:\n"]
            import re as _re
            for d in drafts[:15]:
                to_m = _re.search(r"\*\*TO:\*\*\s*(.+?)(?:\n|$)", d.read_text(encoding="utf-8"))
                to_line = to_m.group(1).strip() if to_m else d.stem
                lines.append(f"• {to_line}")
            if len(drafts) > 15:
                lines.append(f"... and {len(drafts) - 15} more")
            lines.append(f"\nRun /send_batch {n} again within 60s to confirm.")
            await update.message.reply_text("\n".join(lines))
            async def _reset_batch():
                await asyncio.sleep(60)
                _pending_send_batch.pop(chat_id, None)
            asyncio.create_task(_reset_batch())
        else:
            confirmed_drafts = _pending_send_batch.pop(chat_id)
            await update.message.reply_text(f"📤 Sending {len(confirmed_drafts)} email(s)...")
            import subprocess
            loop = asyncio.get_event_loop()
            # Build file filter from draft names
            names = ",".join(d.stem for d in confirmed_drafts)
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["python", "send_cw_outreach.py", "--all", "--files", names],
                    capture_output=True, text=True,
                    cwd=str(BASE_DIR)
                )
            )
            out = (result.stdout or "") + (result.stderr or "")
            await update.message.reply_text(f"Result:\n{out[:3000]}")

    async def cmd_mark_replied(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        email = " ".join(context.args).strip() if context.args else ""
        if not email or "@" not in email:
            await update.message.reply_text("Usage: /mark_replied <email@domain.com>")
            return
        loop = asyncio.get_event_loop()
        count, msg = await loop.run_in_executor(None, lambda: mark_contact_replied(email))
        await update.message.reply_text(msg)

    async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Free-text Gemini chat."""
        if not update.message or not update.message.text:
            return
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not _auth(chat_id):
            await update.message.reply_text("未授权使用此 bot。")
            return
        user_text = update.message.text.strip()
        if not user_text:
            return
        if not GEMINI_API_KEY:
            await update.message.reply_text(
                "Free-text chat requires GEMINI_API_KEY in .env.\n"
                "Available commands: /pending /summary /approve /pipeline_status "
                "/followup_check /followup_send /send_batch /mark_replied"
            )
            return
        await update.message.reply_chat_action("typing")
        ctx = get_agent_context()
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, lambda: call_gemini_agent(user_text, ctx))
        if not reply:
            reply = "No reply from model — please try again."
        if len(reply) > MAX_TELEGRAM_MESSAGE:
            reply = reply[: MAX_TELEGRAM_MESSAGE - 20] + "\n…(truncated)"
        await update.message.reply_text(reply)

    start_text = (
        "BCC Sales Automation Bot\n\n"
        "Pipeline:\n"
        "  /pipeline_status — checkpoint status\n"
        "  /followup_check  — who's due for follow-up\n"
        "  /followup_send   — send follow-ups (confirm twice)\n"
        "  /send_batch N    — send top N CW drafts (confirm twice)\n"
        "  /mark_replied <email> — mark contact as replied\n\n"
        "Approvals:\n"
        "  /pending  — list pending drafts\n"
        "  /approve <name> — approve & send a draft\n\n"
        "Info:\n"
        "  /summary — today's briefing\n"
        "  Free-text chat via Gemini"
    )

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(start_text)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("pending",         cmd_pending))
    app.add_handler(CommandHandler("summary",         cmd_summary))
    app.add_handler(CommandHandler("approve",         cmd_approve))
    app.add_handler(CommandHandler("start",           cmd_start))
    app.add_handler(CommandHandler("pipeline_status", cmd_pipeline_status))
    app.add_handler(CommandHandler("followup_check",  cmd_followup_check))
    app.add_handler(CommandHandler("followup_send",   cmd_followup_send))
    app.add_handler(CommandHandler("send_batch",      cmd_send_batch))
    app.add_handler(CommandHandler("mark_replied",    cmd_mark_replied))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    print("BCC Telegram Bot started. Send /start for command list.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Telegram Bot：手机端审批与简报")
    ap.add_argument("--summary", action="store_true", help="仅打印今日简报到控制台")
    ap.add_argument("--pending", action="store_true", help="仅打印待审批列表到控制台")
    args = ap.parse_args()
    if args.summary:
        print(get_summary_text())
        return
    if args.pending:
        for n, _ in get_pending_drafts():
            print(n)
        return
    run_polling()


if __name__ == "__main__":
    main()
