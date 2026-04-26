"""
通过 CDP 接管用户已打开的 BCC 调试 Chrome，完成 BuildingConnected 的 Autodesk SSO 登录。

登录流程（从记忆中取）：
1. BC 邮箱页：caoyueno5@gmail.com → 点继续
2. Autodesk 页：admin@buildingcodeconsulting.com / 110428Cy### + 勾「Stay signed in 30 days」
3. 如果提示 2FA：停在页面等 Kyle 人工读邮箱里的 6 位码，用户手动输入

前提：已运行 launch_chrome_debug.bat（或等价命令）→ CDP 9222 已监听
"""
import asyncio
import sys

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"
BC_LOGIN_EMAIL = "caoyueno5@gmail.com"
AUTODESK_EMAIL = "admin@buildingcodeconsulting.com"
AUTODESK_PASS = "110428Cy###"
BC_START = "https://app.buildingconnected.com/"


async def run():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"[ERROR] 无法连接到 CDP ({CDP_URL})：{e}")
            print("请先运行 launch_chrome_debug.bat")
            return 1

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        # 找到或打开一个 BC 标签
        page = None
        for pg in context.pages:
            u = (pg.url or "").lower()
            if "buildingconnected" in u or "autodesk" in u:
                page = pg
                break
        if page is None:
            page = context.pages[0] if context.pages else await context.new_page()

        try:
            if "buildingconnected" not in (page.url or "") and "autodesk" not in (page.url or ""):
                print(f"[INFO] 导航到 {BC_START}")
                await page.goto(BC_START, wait_until="domcontentloaded", timeout=30000)

            await asyncio.sleep(2)
            print(f"[INFO] 当前页面: {page.url}")

            # ---- Step 1: BC email prompt (若出现) ----
            # BC 首页会问 email → 然后跳 Autodesk
            for attempt in range(3):
                url = page.url.lower()
                if "accounts.autodesk.com" in url or "identity.autodesk.com" in url:
                    break
                # 尝试找 BC email 输入框（常见 id/占位符）
                email_input = page.locator(
                    "input[type='email'], input[name='email'], #emailField, input[placeholder*='mail' i]"
                ).first
                if await email_input.count() > 0:
                    val = await email_input.input_value()
                    if not val:
                        print(f"[STEP 1] 填入 BC email: {BC_LOGIN_EMAIL}")
                        await email_input.fill(BC_LOGIN_EMAIL)
                        # 点 Next / Continue
                        next_btn = page.get_by_role("button", name=lambda n: n and ("next" in n.lower() or "continue" in n.lower() or "sign" in n.lower()))
                        if await next_btn.count() > 0:
                            await next_btn.first.click()
                        else:
                            await email_input.press("Enter")
                        await asyncio.sleep(3)
                        continue
                await asyncio.sleep(2)

            print(f"[INFO] Step 1 之后 URL: {page.url}")

            # ---- Step 2: Autodesk login ----
            # Autodesk 先问 username/email，再问 password（两步分屏）
            url = page.url.lower()
            if "autodesk.com" in url:
                # 填 username
                uname = page.locator("input[type='email'], input[name='userName'], input[name='username'], #userName").first
                if await uname.count() > 0:
                    val = await uname.input_value()
                    if not val:
                        print(f"[STEP 2a] 填入 Autodesk email: {AUTODESK_EMAIL}")
                        await uname.fill(AUTODESK_EMAIL)
                    # 点 Next
                    next_btn = page.locator("button[type='submit'], #verify_user_btn")
                    if await next_btn.count() > 0:
                        try:
                            await next_btn.first.click()
                        except Exception:
                            await uname.press("Enter")
                    else:
                        await uname.press("Enter")
                    await asyncio.sleep(3)

                # 填 password
                pwd = page.locator("input[type='password'], #password").first
                if await pwd.count() > 0:
                    val = await pwd.input_value()
                    if not val:
                        print("[STEP 2b] 填入 Autodesk 密码")
                        await pwd.fill(AUTODESK_PASS)

                    # 勾 "Stay signed in" — 常见 label "Stay signed in", "Keep me signed in", "Remember me"
                    stay_checked = False
                    for sel in [
                        "input[name='staySignedIn']",
                        "input#persistent_login",
                        "input[type='checkbox'][name*='stay' i]",
                        "input[type='checkbox'][name*='remember' i]",
                    ]:
                        try:
                            cb = page.locator(sel).first
                            if await cb.count() > 0:
                                is_checked = await cb.is_checked()
                                if not is_checked:
                                    print(f"[STEP 2c] 勾上 Stay signed in ({sel})")
                                    await cb.check()
                                stay_checked = True
                                break
                        except Exception:
                            continue
                    if not stay_checked:
                        # 兜底：按 label 文本找
                        try:
                            label = page.get_by_text("Stay signed in", exact=False)
                            if await label.count() > 0:
                                print("[STEP 2c] 通过 label 勾 Stay signed in")
                                await label.first.click()
                                stay_checked = True
                        except Exception:
                            pass
                    if not stay_checked:
                        print("[WARN] 没找到 Stay signed in 复选框 — 请手动勾一下")

                    submit = page.locator("button[type='submit'], #btnSubmit, button:has-text('Sign in')")
                    if await submit.count() > 0:
                        print("[STEP 2d] 提交登录")
                        await submit.first.click()
                    else:
                        await pwd.press("Enter")
                    await asyncio.sleep(5)

            # ---- Step 3: 2FA 处理 ----
            url = page.url.lower()
            # 2FA 页面 URL 或内容识别（常见：/secondary-verify, verifyOtp, passcode）
            body_text = ""
            try:
                body_text = (await page.locator("body").inner_text()).lower()
            except Exception:
                pass
            if any(k in url for k in ["verify", "otp", "mfa", "2fa"]) or any(
                k in body_text for k in ["verification code", "passcode", "2-step", "two-step", "6-digit"]
            ):
                print()
                print("=" * 60)
                print("[2FA] Autodesk 要求 6 位验证码。")
                print("     请检查 admin@buildingcodeconsulting.com 邮箱置顶邮件，")
                print("     把 6 位码在 Chrome 窗口里手动输入并提交。")
                print("     输入完成后按 Enter 让脚本继续。")
                print("=" * 60)
                try:
                    input("按 Enter 继续...")
                except EOFError:
                    pass

            # 最终检查
            await asyncio.sleep(2)
            print(f"[DONE] 最终 URL: {page.url}")
            if "app.buildingconnected.com" in (page.url or "") and "autodesk" not in (page.url or ""):
                print("[OK] 看起来已登录 BuildingConnected ✓")
                return 0
            else:
                print("[?] 可能还没完全登录，请人工确认该 Chrome 窗口的状态。")
                return 0
        finally:
            try:
                await browser.close()  # 只断开 CDP，不关窗口
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
