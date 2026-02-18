"""
Google / Gemini 网页版登录助手：有头浏览器，手动登录 Google 并停留在 Gemini 页面后保存 Cookie。
与 ConstructionWire 相同套路：下次 gemini_web_automation.py 可直接加载 .google_cookies.json，无需每次扫码/输密码。
"""
import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from playwright.async_api import async_playwright

GEMINI_URL = "https://gemini.google.com"
COOKIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".google_cookies.json")


def has_saved_cookies() -> bool:
    """是否存在已保存的 Google/Gemini 登录状态。"""
    return os.path.isfile(COOKIES_PATH)


def is_on_gemini_ready(url: str) -> bool:
    """当前已在 Gemini 页面且非登录/选账号页。"""
    if not url:
        return False
    return "gemini.google.com" in url and "accounts.google.com" not in url


async def wait_for_gemini_ready(page, timeout_ms: int = 300_000):
    """
    轮询直到：URL 为 gemini.google.com 且已离开 accounts（登录完成）。
    超时则抛出 asyncio.TimeoutError。
    """
    deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
    while asyncio.get_event_loop().time() < deadline:
        if is_on_gemini_ready(page.url):
            return True
        await asyncio.sleep(1.0)
    raise asyncio.TimeoutError("未在限定时间内进入 Gemini 页面，请完成登录并停留在 gemini.google.com 后重试。")


async def save_cookies(context):
    """将当前 context 的 Cookie 与本地存储保存到 .google_cookies.json。"""
    await context.storage_state(path=COOKIES_PATH)
    print(f"已保存登录状态到: {COOKIES_PATH}")


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        print("正在打开 Gemini 网页版。若跳转到 Google 登录，请手动完成登录并停留在 Gemini 页面…")
        await page.goto(GEMINI_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle", timeout=20000)

        try:
            await wait_for_gemini_ready(page, timeout_ms=300_000)
            await save_cookies(context)
            print("登录成功，Cookie 已保存。后续可使用 gemini_web_automation.py 免密调用网页版 Gemini。")
        except asyncio.TimeoutError as e:
            print(e)
            return 1
        finally:
            await browser.close()

    return 0


def main():
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
