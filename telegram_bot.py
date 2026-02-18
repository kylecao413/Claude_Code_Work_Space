"""
Telegram 手机端 AI 交互：列出待审批草稿、审批发送、今日简报，自由对话（Gemini），以及 /save 将对话封装为 Cursor 任务（写入 Inbox/ACTIVE_TASK.md）。
需在 .env 中配置 TELEGRAM_BOT_TOKEN、TELEGRAM_ALLOWED_CHAT_IDS；自由对话与 /save 需 GEMINI_API_KEY。
"""
import asyncio
import os
import sys
from collections import deque
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
_env_inbox = os.environ.get("INBOX_DIR", "").strip().strip('"') or os.environ.get("BRIDGE_DIR", "").strip().strip('"')
INBOX_DIR = Path(_env_inbox) if _env_inbox else BASE_DIR / "Inbox"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"')
MAX_TELEGRAM_MESSAGE = 4000
MAX_CHAT_HISTORY = 20
# 每个 chat_id 最近 N 条对话（user/assistant 交替），供 /save 回溯
_chat_history: dict[int, deque] = {}


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


def _get_history(chat_id: int) -> deque:
    if chat_id not in _chat_history:
        _chat_history[chat_id] = deque(maxlen=MAX_CHAT_HISTORY)
    return _chat_history[chat_id]


def _summarize_conversation_to_task(history_list: list[dict]) -> str:
    """用 Gemini 将对话总结为 Cursor 可执行的任务单（Markdown）。"""
    if not history_list or not GEMINI_API_KEY:
        return ""
    conv = "\n".join(
        f"**{h['role']}**: {h['text'][:2000]}" for h in history_list
    )
    prompt = f"""你正在为 Building Code Consulting 的 Cursor Agent 生成任务单。用户 Yue Cao (PE, MCP) 在 Telegram 上与 Bot 的对话如下：

{conv}

请将上述对话总结为一份**标准 Markdown 任务单**，包含：
1. **项目/客户**：提到的项目名（如 2121 Virginia Ave、Carr Properties）或客户名。
2. **业务逻辑与规范**：用户提到的规范章节、审查类型（如 Third-Party Peer Review、24-hour Combo Inspections）、邮件或代码相关要求。
3. **具体执行要求**：需要 Cursor 执行的修改（如更新 Outbound 草稿、修改 gemini_web_automation 参数、增加对某项目的描述等）。
4. 末尾加一句：**基于 Yue Cao (PE, MCP) 的专业资质建议。**

输出仅包含 Markdown 任务单正文，不要额外解释。"""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        for model_id in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-001"):
            try:
                response = client.models.generate_content(model=model_id, contents=prompt)
                if response and getattr(response, "text", None):
                    return response.text.strip()
            except Exception:
                continue
    except Exception:
        pass
    return ""


def _write_active_task_and_archive(markdown_content: str) -> tuple[Path, Path | None]:
    """将任务写入 Inbox/ACTIVE_TASK.md（顶部追加带时间戳的新块），并备份到 Inbox/Archive/Task_YYYYMMDD_HHMM.md。"""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    archive_dir = INBOX_DIR / "Archive"
    archive_dir.mkdir(exist_ok=True)
    active_path = INBOX_DIR / "ACTIVE_TASK.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_block = f"---\n\n## 来自 Telegram · {ts}\n\n{markdown_content}\n\n"
    if active_path.exists():
        existing = active_path.read_text(encoding="utf-8")
        active_path.write_text(new_block + existing, encoding="utf-8")
    else:
        active_path.write_text("# ACTIVE TASK（由 Telegram Bot /save 同步）\n\n" + new_block, encoding="utf-8")
    archive_name = f"Task_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    archive_path = archive_dir / archive_name
    archive_path.write_text("# 任务备份\n\n" + new_block, encoding="utf-8")
    return active_path, archive_path


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

    async def do_save_task(chat_id: int) -> str:
        """执行保存任务：取最近对话 → Gemini 总结 → 写入 ACTIVE_TASK.md + Archive。"""
        history = list(_get_history(chat_id))
        if not history:
            return "暂无对话记录，请先与我讨论要执行的任务后再用 /save 或说「存为任务」。"
        loop = asyncio.get_event_loop()
        task_md = await loop.run_in_executor(None, lambda: _summarize_conversation_to_task(history))
        if not task_md:
            return "任务总结失败，请稍后再试。"
        active_path, archive_path = _write_active_task_and_archive(task_md)
        return f"✅ 任务已同步至 Cursor。\n\n· 主文件：{active_path.name}（Inbox 或云盘）\n· 备份：Archive/{archive_path.name if archive_path else ''}\n\nCursor 检测到 ACTIVE_TASK.md 更新后会按任务执行，完成后会在 TASK_STATUS.md 中反馈。"

    async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _auth(update.effective_chat.id if update.effective_chat else None):
            await update.message.reply_text("未授权使用此 bot。")
            return
        await update.message.reply_chat_action("typing")
        chat_id = update.effective_chat.id if update.effective_chat else 0
        msg = await do_save_task(chat_id)
        await update.message.reply_text(msg)

    async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """自由对话：记录历史、识别「存为任务」意图、或转发 Gemini 并回复。"""
        if not update.message or not update.message.text:
            return
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not _auth(chat_id):
            await update.message.reply_text("未授权使用此 bot。")
            return
        user_text = update.message.text.strip()
        if not user_text:
            return
        # 意图识别：自然语言保存任务
        save_keywords = ("存为任务", "保存任务", "存成任务", "save as task", "保存为任务", "同步到 cursor")
        if any(k in user_text.lower() for k in save_keywords):
            _get_history(chat_id or 0).append({"role": "user", "text": user_text})
            await update.message.reply_chat_action("typing")
            msg = await do_save_task(chat_id or 0)
            await update.message.reply_text(msg)
            return
        if not GEMINI_API_KEY:
            await update.message.reply_text(
                "我目前只响应命令：/pending、/summary、/approve、/save。\n\n"
                "若要自由对话或 /save 总结任务，请在 .env 中配置 GEMINI_API_KEY，然后重启 bot。"
            )
            return
        _get_history(chat_id or 0).append({"role": "user", "text": user_text})
        await update.message.reply_chat_action("typing")
        ctx = get_agent_context()
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, lambda: call_gemini_agent(user_text, ctx))
        if not reply:
            reply = "没有收到模型回复，请稍后再试。"
        if len(reply) > MAX_TELEGRAM_MESSAGE:
            reply = reply[: MAX_TELEGRAM_MESSAGE - 20] + "\n…(已截断)"
        _get_history(chat_id or 0).append({"role": "assistant", "text": reply})
        await update.message.reply_text(reply)

    start_text = (
        "BCC 销售自动化 Bot。\n"
        "命令: /pending 待审批 | /summary 今日简报 | /approve <名称> 审批发送 | /save 将最近对话存为 Cursor 任务\n"
        "直接发文字可与我对话；说「存为任务」或发 /save 可将讨论同步到 Inbox/ACTIVE_TASK.md，由 Cursor 执行。"
    )

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(start_text)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    print("Telegram Bot 已启动。发送 /start 查看命令；直接发消息可对话（需 GEMINI_API_KEY）。")
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
