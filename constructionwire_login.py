"""
ConstructionWire 登录助手：有头浏览器，手动输入账号与验证码，登录成功后自动保存 Cookie。
下次可优先加载 Cookie，无需再输入密码（Cookie 失效时再运行本脚本重新登录即可）。
"""
import asyncio
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from playwright.async_api import async_playwright

LOGIN_URL = "https://www.constructionwire.com/Login"
# 登录成功后通常会跳离 /Login，或出现仅登录后可见的页面
COOKIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".constructionwire_cookies.json")


def has_saved_cookies() -> bool:
    """是否存在已保存的登录状态（供其他脚本判断是否可免密）。"""
    return os.path.isfile(COOKIES_PATH)


def _on_login_page(url: str) -> bool:
    """URL still on the login page (case-insensitive)."""
    u = (url or "").lower()
    return "constructionwire.com" in u and "/login" in u


def _on_app_page(url: str) -> bool:
    """URL is on ConstructionWire app but past the login page."""
    u = (url or "").lower()
    return "constructionwire.com" in u and "/login" not in u and not u.startswith("about:")


def is_logged_in_url(url: str) -> bool:
    """Backward-compat alias for downstream importers (pipeline scripts).
    Returns True iff the URL is past the login page (i.e. inside the app)."""
    return _on_app_page(url)


async def wait_for_login_success(page, timeout_ms: int = 300_000):
    """
    Two-stage wait:
      1. Confirm we actually arrived at the /Login page (URL contains /Login).
         If we already land on the app (cookies still valid), short-circuit success.
      2. Wait for URL to leave /Login (i.e. user finished login).
    Avoids the about:blank false-positive from the original loose `'/Login' not in url` check.
    """
    deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)

    # Stage 1: confirm landing
    landed_on_login = False
    while asyncio.get_event_loop().time() < deadline:
        url = page.url
        if _on_login_page(url):
            landed_on_login = True
            break
        if _on_app_page(url):
            # Already authenticated via residual cookies
            print(f"未到登录页就直接进入应用 ({url}) —— cookies 未失效,直接保存。")
            return True
        await asyncio.sleep(1.0)

    if not landed_on_login:
        raise asyncio.TimeoutError("未到达登录页,无法继续。")

    print(f"已到达登录页 ({page.url})。请在浏览器中手动登录,登录后窗口会自动关闭并保存 cookies…")

    # Stage 2: wait for URL to leave /Login
    while asyncio.get_event_loop().time() < deadline:
        url = page.url
        if _on_app_page(url):
            print(f"检测到登录成功,跳转到 {url}")
            await asyncio.sleep(2.0)  # let session storage settle
            return True
        await asyncio.sleep(1.5)

    raise asyncio.TimeoutError("登录超时 (5 min) —— 请重试。")


async def save_cookies(context):
    """将当前 context 的 Cookie 与本地存储保存到本地文件，供下次使用。"""
    await context.storage_state(path=COOKIES_PATH)
    print(f"已保存登录状态到: {COOKIES_PATH}")


async def run():
    async with async_playwright() as p:
        # 有头模式，便于你手动输入账号和图形验证码
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        print("正在打开 ConstructionWire 登录页，请在浏览器中手动输入账号与验证码并完成登录…")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle", timeout=15000)

        try:
            await wait_for_login_success(page, timeout_ms=300_000)
            await save_cookies(context)
            print("登录成功，Cookie 已保存。后续脚本可使用该 Cookie 免密访问。")
        except asyncio.TimeoutError as e:
            print(e)
            return 1
        finally:
            await browser.close()

    return 0


def main():
    sys.exit(asyncio.run(run()))


# 其他脚本使用方式示例（免密）：
#   from playwright.async_api import async_playwright
#   from constructionwire_login import COOKIES_PATH, has_saved_cookies
#   context = await browser.new_context(storage_state=COOKIES_PATH)  # 仅当 has_saved_cookies() 时使用


if __name__ == "__main__":
    main()
