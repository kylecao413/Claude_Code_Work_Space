"""
core_tools/browser_connect.py

统一的浏览器启动入口：
1. 优先尝试通过 CDP 连接到用户已开的 Chrome（端口 9222）——复用用户已登录的会话，不再注入 Cookie。
2. 连接失败时，回退到传统的 Playwright launch + storage_state/Cookie 注入模式。

用法：
    from core_tools.browser_connect import open_browser, close_browser

    async with async_playwright() as p:
        browser, context, page, attached = await open_browser(
            p,
            cookies_path=".buildingconnected_cookies.json",
            cookies_format="cookies_list",   # 或 "storage_state"
            target_url="https://app.buildingconnected.com",
            headless=False,
        )
        # ... 使用 page ...
        await close_browser(browser, context, attached)

注意：attached=True 时 close_browser() 只断开 CDP 连接，不会关闭用户的 Chrome 窗口。
"""
from __future__ import annotations

import json
import os
from typing import Literal, Optional

from playwright.async_api import Playwright

CDP_URL = os.environ.get("BCC_CDP_URL", "http://127.0.0.1:9222")
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

CookiesFormat = Literal["storage_state", "cookies_list"]


def _url_host(url: str) -> str:
    if not url or "://" not in url:
        return ""
    return url.split("/", 3)[2].lower()


async def _pick_page_for_host(context, host: str):
    if not host:
        return None
    for pg in context.pages:
        try:
            if host in (pg.url or "").lower():
                return pg
        except Exception:
            continue
    return None


async def open_browser(
    p: Playwright,
    *,
    cookies_path: Optional[str] = None,
    cookies_format: CookiesFormat = "storage_state",
    target_url: Optional[str] = None,
    headless: bool = False,
    viewport: Optional[dict] = None,
    user_agent: Optional[str] = None,
    goto_on_attach: bool = True,
):
    """
    返回 (browser, context, page, attached_to_cdp)。

    - 先试 CDP 连接。成功则复用 browser.contexts[0] 中目标域名下已存在的页面；没有就 new_page()。
    - 失败则 launch() 新 Chromium + 注入 cookies（两种格式兼容）。
    """
    viewport = viewport or {"width": 1280, "height": 720}
    user_agent = user_agent or DEFAULT_UA
    host = _url_host(target_url or "")

    # ---- 1. 尝试 CDP ----
    try:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        print(f"[browser_connect] 已通过 CDP 连接到本机 Chrome ({CDP_URL})。")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await _pick_page_for_host(context, host)
        if page is None:
            page = context.pages[0] if context.pages else await context.new_page()
            if target_url and goto_on_attach:
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print(f"[browser_connect] 导航到 {target_url} 失败: {e}")
        else:
            print(f"[browser_connect] 复用当前标签页: {page.url}")
        return browser, context, page, True
    except Exception as e:
        print(f"[browser_connect] 未检测到 CDP（{CDP_URL}）。回退到独立 Chromium 启动。原因: {e}")

    # ---- 2. 回退：launch + cookies ----
    browser = await p.chromium.launch(headless=headless)
    ctx_kwargs: dict = {"viewport": viewport, "user_agent": user_agent}

    if cookies_path and os.path.exists(cookies_path) and cookies_format == "storage_state":
        ctx_kwargs["storage_state"] = cookies_path

    context = await browser.new_context(**ctx_kwargs)

    if cookies_path and os.path.exists(cookies_path) and cookies_format == "cookies_list":
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                storage = json.load(f)
            cookies = storage.get("cookies") if isinstance(storage, dict) else storage
            if cookies:
                await context.add_cookies(cookies)
        except Exception as e:
            print(f"[browser_connect] 加载 Cookie 失败: {e}")

    page = await context.new_page()
    if target_url:
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"[browser_connect] 导航到 {target_url} 失败: {e}")
    return browser, context, page, False


async def close_browser(browser, context, attached: bool):
    """
    安全关闭。
    - CDP 模式：只断开连接，不关闭用户的 Chrome。
    - 回退模式：关闭整个 browser。
    """
    try:
        if attached:
            await browser.close()  # CDP: 仅断开
        else:
            try:
                await context.close()
            except Exception:
                pass
            await browser.close()
    except Exception as e:
        print(f"[browser_connect] 关闭时出错（忽略）: {e}")


async def save_storage_state(context, path: str) -> None:
    """把当前 context 的登录态写回 cookies_path（Playwright 原生 storage_state 格式）。"""
    try:
        await context.storage_state(path=path)
        print(f"[browser_connect] 已保存 storage_state 到 {path}")
    except Exception as e:
        print(f"[browser_connect] 保存 storage_state 失败: {e}")
