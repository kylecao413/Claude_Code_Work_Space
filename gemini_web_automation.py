"""
Gemini 网页版自动化：用已保存的 Google Cookie 打开 Gemini，输入深度调研指令，等待完成后抓取结果并保存。
零 API 成本，使用网页端 Deep Research 等能力。采用“文字匹配 + 多选择器回退”提高 DOM 变更时的耐用性。
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from playwright.async_api import async_playwright, Page

# 与 google_gemini_login 一致
COOKIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".google_cookies.json")
GEMINI_URL = "https://gemini.google.com"

# Deep Research 可能很久，默认最多等 10 分钟
DEFAULT_RESPONSE_TIMEOUT_MS = 600_000


def _company_to_filename(company: str) -> str:
    """将公司名转为可作文件名的字符串（Research_[Company].md）。"""
    s = re.sub(r"[^\w\s\-]", "", (company or "").strip())
    s = re.sub(r"\s+", "_", s).strip("_") or "Company"
    return s


async def _find_input_box(page: Page):
    """
    用多种方式定位 Gemini 输入框，减少 DOM 变更影响。
    优先：role=textbox、placeholder 含 prompt/enter/message、textarea、contenteditable。
    """
    candidates = [
        page.get_by_role("textbox"),
        page.get_by_placeholder("Enter a prompt here"),
        page.get_by_placeholder("Message Gemini"),
        page.get_by_placeholder("Ask Gemini"),
        page.get_by_placeholder("Prompt"),
        page.locator("textarea").first,
        page.locator('[contenteditable="true"]').first,
    ]
    for loc in candidates:
        try:
            if await loc.count() > 0:
                return loc.first
        except Exception:
            continue
    return None


async def _find_send_button(page: Page):
    """定位发送按钮：aria-label、按钮文字、或包含 send 图标的可点击元素。"""
    # Use flag 2 (IGNORECASE) directly to avoid re.I/re.IGNORECASE attribute issues in some envs
    send_pattern = re.compile(r"send|submit", 2)
    candidates = [
        page.get_by_role("button", name=send_pattern),
        page.locator('button[aria-label*="Send"]'),
        page.locator('button[aria-label*="Submit"]'),
        page.get_by_label("Send"),
        page.locator('button:has(svg)').last,
    ]
    for loc in candidates:
        try:
            if await loc.count() > 0:
                return loc.first
        except Exception:
            continue
    return None


async def _find_attach_button(page: Page):
    """
    定位 Gemini 输入区旁的「+」按钮；点击后弹出菜单（Upload files / Add from Drive 等）。
    """
    candidates = [
        page.get_by_role("button", name=re.compile(r"add files|add file", 2)),
        page.locator('[aria-label*="Add files" i], [aria-label*="Add file" i]'),
        page.get_by_title("Add files"),
        page.get_by_title("Add file"),
        page.get_by_role("button", name=re.compile(r"attach|upload|add", 2)),
        page.locator('button[aria-label*="Attach"]'),
        page.locator('button[aria-label*="Upload"]'),
        page.locator('button[aria-label*="Add"]'),
        page.locator('[aria-label*="attach" i]'),
        page.locator('button:has-text("+")').first,
        page.locator('[data-tooltip*="add files" i], [data-tooltip*="attach" i]'),
        page.locator('button').filter(has=page.locator('svg')).first,
    ]
    for loc in candidates:
        try:
            if await loc.count() > 0:
                return loc.first
        except Exception:
            continue
    return None


async def _find_upload_files_menu_item(page: Page):
    """
    在「+」弹出的菜单中定位 "Upload files" 选项；点击后才会弹出系统文件选择器。
    优先在 menu/popover 内查找，避免点到页面其他同名文字。
    """
    # Prefer inside a menu/popover so we don't click a chip or other "Upload files" on the page
    menu_scope = page.locator('[role="menu"], [role="listbox"], [data-menu], [class*="menu"]').first
    candidates = [
        menu_scope.locator('text="Upload files"').first,
        menu_scope.locator('text="Upload file"').first,
        page.get_by_role("menuitem", name=re.compile(r"upload files?", 2)),
        page.get_by_role("option", name=re.compile(r"upload files?", 2)),
        page.locator('[role="menuitem"]:has-text("Upload files")').first,
        page.get_by_text("Upload files", exact=True),
        page.get_by_text("Upload file", exact=True),
        page.locator('text="Upload files"').first,
        page.locator('text="Upload file"').first,
    ]
    for loc in candidates:
        try:
            if await loc.count() > 0:
                return loc.first
        except Exception:
            continue
    return None


async def _wait_for_thinking_done(page: Page, timeout_ms: int) -> bool:
    """
    等待“Thinking”/“Searching”等加载状态消失，或超时。
    通过轮询页面文本是否仍包含这些关键词实现，避免依赖固定 class。
    """
    deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
    last_len = 0
    stable_rounds = 0
    while asyncio.get_event_loop().time() < deadline:
        try:
            body = await page.locator("body").inner_text()
            lower = body.lower()
            if "thinking" in lower or "searching" in lower or "generating" in lower:
                await asyncio.sleep(2.0)
                continue
            # 无加载词且内容长度稳定几轮，视为完成
            if len(body) == last_len:
                stable_rounds += 1
                if stable_rounds >= 3:
                    return True
            else:
                stable_rounds = 0
            last_len = len(body)
        except Exception:
            pass
        await asyncio.sleep(2.0)
    return True  # 超时也返回，尽量抓取已有内容


async def _extract_response_text(page: Page) -> str:
    """
    从页面提取 Gemini 回复正文。优先取 main、对话区域或最后一块长文本。
    """
    selectors = [
        'main',
        '[role="main"]',
        'article',
        '[data-message-author="model"]',
        '.message-content',
        '[class*="response"]',
        '[class*="output"]',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).last
            if await loc.count() > 0:
                text = await loc.inner_text()
                if len(text.strip()) > 100:
                    return text.strip()
        except Exception:
            continue
    try:
        return (await page.locator("body").inner_text()).strip()
    except Exception:
        return ""


def _default_prompt(company: str) -> str:
    """默认深度调研话术（可被调用方覆盖）。"""
    return (
        f"请利用 Deep Research 功能，帮我找到 {company} 在 DC 的 specific projects "
        "a couple (2 to 4 if possible) best point of contacts。"
    )


async def run_gemini_web_research(
    company_name: str,
    *,
    prompt: str | None = None,
    response_timeout_ms: int = DEFAULT_RESPONSE_TIMEOUT_MS,
    save_research_path: str | None = None,
    create_draft: bool = True,
    headless: bool = False,
    attachment_path: str | Path | None = None,
) -> dict:
    """
    执行一次 Gemini 网页版深度调研并保存结果。

    :param company_name: 公司名，用于默认 prompt 与文件名。
    :param prompt: 若提供则覆盖默认 prompt。
    :param response_timeout_ms: 等待回复的最长时间（毫秒）。
    :param save_research_path: 若提供则覆盖默认 Research_[Company].md 路径。
    :param create_draft: 是否在 Pending_Approval/ 下生成邮件草稿占位。
    :param headless: 是否无头模式（建议首次 False 以便观察/处理验证码）。
    :param attachment_path: 可选。要上传到 Gemini 的本地文件路径（如 .docx/.pdf），会点击「+」并选择该文件后再发送 prompt。
    :return: {"success": bool, "research_path": str, "draft_path": str|None, "response_preview": str}
    """
    if not os.path.isfile(COOKIES_PATH):
        return {
            "success": False,
            "research_path": "",
            "draft_path": None,
            "response_preview": "",
            "response_full": "",
            "error": "未找到 .google_cookies.json。请按 GEMINI_LOGIN_WITH_CHROME.md 做一次完整登录：1) 关闭所有 Chrome 2) 运行 start_chrome_for_gemini_login.bat 3) 在 Chrome 里打开 gemini.google.com 并登录 4) 运行 python google_gemini_login_chrome.py",
        }

    base_dir = Path(__file__).resolve().parent
    safe_name = _company_to_filename(company_name)
    research_path = save_research_path or str(base_dir / f"Research_{safe_name}.md")
    prompt_text = (prompt or _default_prompt(company_name)).strip()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            storage_state=COOKIES_PATH,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            await page.goto(GEMINI_URL, wait_until="domcontentloaded")
            # Don't wait for networkidle - Gemini often keeps connections open. Wait for page to settle then look for input.
            await page.wait_for_load_state("load", timeout=15000)
            await asyncio.sleep(2)

            # 若被重定向到登录页，提示需要重新跑 google_gemini_login
            if "accounts.google.com" in page.url:
                return {
                    "success": False,
                    "research_path": "",
                    "draft_path": None,
                    "response_preview": "",
                    "response_full": "",
                    "error": "当前被重定向到 Google 登录页，Cookie 已失效。请做一次 100% 重新登录：见 GEMINI_LOGIN_WITH_CHROME.md（关闭所有 Chrome → start_chrome_for_gemini_login.bat → 登录 Gemini → python google_gemini_login_chrome.py）",
                }

            input_box = await _find_input_box(page)
            if not input_box:
                return {
                    "success": False,
                    "research_path": "",
                    "draft_path": None,
                    "response_preview": "",
                    "response_full": "",
                    "error": "未在页面上找到输入框，Gemini 界面可能已改版，请检查或手动操作。",
                }

            # Optional: upload file via the "+" / Attach button so it’s in context before sending the prompt
            if attachment_path:
                path = Path(attachment_path).resolve()
                if not path.is_file():
                    return {
                        "success": False,
                        "research_path": "",
                        "draft_path": None,
                        "response_preview": "",
                        "response_full": "",
                        "error": f"附件不存在: {path}",
                    }
                attach_btn = await _find_attach_button(page)
                if not attach_btn:
                    return {
                        "success": False,
                        "research_path": "",
                        "draft_path": None,
                        "response_preview": "",
                        "response_full": "",
                        "error": "未找到「+」/附件按钮，无法上传文件。请确认 Gemini 页面已加载完整。",
                    }
                try:
                    # Two-step flow: (1) click "+" to open menu, (2) click "Upload files" → native file chooser opens
                    await attach_btn.click()
                    await asyncio.sleep(0.8)
                    upload_files_btn = await _find_upload_files_menu_item(page)
                    if not upload_files_btn:
                        return {
                            "success": False,
                            "research_path": "",
                            "draft_path": None,
                            "response_preview": "",
                            "response_full": "",
                            "error": "点击「+」后未找到「Upload files」菜单项。",
                        }
                    async with page.expect_file_chooser(timeout=15000) as fc_info:
                        await upload_files_btn.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(str(path))
                    # Wait for file to appear in Gemini context before we send the prompt
                    await asyncio.sleep(4)
                except Exception as e:
                    return {
                        "success": False,
                        "research_path": "",
                        "draft_path": None,
                        "response_preview": "",
                        "response_full": "",
                        "error": f"上传附件时出错: {e}",
                    }
                # Re-find input so we use the current prompt box after the attachment is in context
                input_box = await _find_input_box(page)
                if not input_box:
                    return {
                        "success": False,
                        "research_path": "",
                        "draft_path": None,
                        "response_preview": "",
                        "response_full": "",
                        "error": "上传完成后未找到输入框。",
                    }

            await input_box.fill(prompt_text)
            await asyncio.sleep(0.5)

            send_btn = await _find_send_button(page)
            if send_btn:
                await send_btn.click()
            else:
                await input_box.press("Enter")

            await _wait_for_thinking_done(page, response_timeout_ms)
            response_text = await _extract_response_text(page)

            # 写入 Research_[Company].md
            with open(research_path, "w", encoding="utf-8") as f:
                f.write(f"# {company_name} — Gemini 网页版 Deep Research 结果\n\n")
                f.write("**来源**：Gemini 网页端（gemini_web_automation.py）\n\n")
                f.write("---\n\n")
                f.write(response_text)
                f.write("\n")

            draft_path = None
            if create_draft:
                _env = os.environ.get("PENDING_APPROVAL_DIR", "").strip().strip('"')
                pending_dir = Path(_env) if _env else base_dir / "Pending_Approval"
                outbound_dir = pending_dir / "Outbound"
                outbound_dir.mkdir(parents=True, exist_ok=True)
                draft_path = str(outbound_dir / f"{safe_name}_Draft.md")
                with open(draft_path, "w", encoding="utf-8") as f:
                    f.write(f"# 邮件草稿：{company_name}\n\n")
                    f.write("（根据 Research 结果由 Agent 或你补充收件人与正文后，将本文件改名为含 `-OK` 或内文加 `APPROVED` 再发送。）\n\n")
                    f.write("---\n\n")
                    f.write("## Research 摘要（可粘贴关键联系人再写邮件）\n\n")
                    f.write(response_text[:8000] + ("…" if len(response_text) > 8000 else ""))
                    f.write("\n")

            return {
                "success": True,
                "research_path": research_path,
                "draft_path": draft_path,
                "response_preview": response_text[:500] + ("…" if len(response_text) > 500 else ""),
                "response_full": response_text,
            }

        except Exception as e:
            return {
                "success": False,
                "research_path": research_path,
                "draft_path": None,
                "response_preview": "",
                "response_full": "",
                "error": str(e),
            }
        finally:
            await browser.close()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Gemini 网页版深度调研（需先运行 google_gemini_login.py 保存 Cookie）")
    ap.add_argument("company", help="公司名，如 Carr Properties")
    ap.add_argument("--prompt", default=None, help="自定义 prompt，不填则用默认 Deep Research 话术")
    ap.add_argument("--timeout", type=int, default=DEFAULT_RESPONSE_TIMEOUT_MS // 1000, help="等待回复秒数（默认 600）")
    ap.add_argument("--no-draft", action="store_true", help="不生成 Pending_Approval 草稿")
    ap.add_argument("--headless", action="store_true", help="无头模式")
    ap.add_argument("--attachment", default=None, help="上传到 Gemini 的本地文件路径（如 .docx/.pdf）")
    args = ap.parse_args()

    result = asyncio.run(
        run_gemini_web_research(
            args.company,
            prompt=args.prompt,
            response_timeout_ms=args.timeout * 1000,
            create_draft=not args.no_draft,
            headless=args.headless,
            attachment_path=args.attachment,
        )
    )

    if result["success"]:
        print(f"Research 已保存: {result['research_path']}")
        if result.get("draft_path"):
            print(f"草稿已生成: {result['draft_path']}")
        print("\n--- 回复摘要 ---\n", result["response_preview"])
        sys.exit(0)
    else:
        print("失败:", result.get("error", "未知错误"), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
