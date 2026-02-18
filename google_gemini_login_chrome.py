"""
使用你本机已打开的 Chrome 完成 Gemini 登录并保存 Cookie，避免 Google 报「此浏览器或应用可能不安全」。
前置条件：先用「远程调试」方式启动 Chrome，再运行本脚本连接该浏览器。
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
CDP_URL = "http://127.0.0.1:9222"


def is_on_gemini_ready(url: str) -> bool:
    if not url:
        return False
    return "gemini.google.com" in url and "accounts.google.com" not in url


async def wait_for_gemini_ready(page, timeout_ms: int = 300_000):
    deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
    while asyncio.get_event_loop().time() < deadline:
        try:
            if is_on_gemini_ready(page.url):
                return True
        except Exception:
            pass
        await asyncio.sleep(1.0)
    raise asyncio.TimeoutError(
        "未在限定时间内进入 Gemini 页面。请在该 Chrome 窗口内完成登录并停留在 gemini.google.com 后重试。"
    )


async def run():
    print("正在连接本机 Chrome（localhost:9222）…")
    print("若尚未用「远程调试」启动 Chrome，请先关闭所有 Chrome 窗口，再运行：")
    print('  start_chrome_for_gemini_login.bat')
    print("或手动执行：")
    print('  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222')
    print()

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"连接失败: {e}")
            print("请确认已用 --remote-debugging-port=9222 启动 Chrome 后再运行本脚本。")
            return 1

        try:
            # 使用已有 context 和页面，或新建一个
            if browser.contexts:
                context = browser.contexts[0]
                if context.pages:
                    page = context.pages[0]
                    if is_on_gemini_ready(page.url):
                        print("已连接。当前标签页已在 Gemini，等待就绪…")
                    else:
                        print("已连接。正在打开 Gemini 页面，请在该 Chrome 窗口中完成登录并停留在 Gemini…")
                        await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=60000)
                        try:
                            await page.wait_for_load_state("load", timeout=15000)
                        except Exception:
                            pass
                else:
                    page = await context.new_page()
                    print("已连接。正在打开 Gemini 页面…")
                    await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=60000)
            else:
                context = await browser.new_context()
                page = await context.new_page()
                print("已连接。正在打开 Gemini 页面…")
                await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=60000)

            await wait_for_gemini_ready(page, timeout_ms=300_000)
            await context.storage_state(path=COOKIES_PATH)
            print(f"登录成功，Cookie 已保存到: {COOKIES_PATH}")
            print("后续可直接运行 gemini_web_automation.py，无需再次登录。")
        except asyncio.TimeoutError as e:
            print(e)
            return 1
        except Exception as e:
            print("错误:", e)
            return 1
        finally:
            # 仅断开连接，不关闭用户正在使用的 Chrome
            try:
                await browser.close()
            except Exception:
                pass

    return 0


def main():
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
