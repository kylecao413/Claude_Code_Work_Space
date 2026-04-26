"""
探查 BC pipeline 页面的 DOM 结构：找到 Undecided / Accepted tab 和 project 列表选择器。
通过 CDP 接管已登录的调试 Chrome。
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"
PIPELINE_URL = "https://app.buildingconnected.com/opportunities/pipeline"
DUMP_DIR = Path("bc_pipeline_dump")


async def run():
    DUMP_DIR.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        # 选 BC 的页
        page = None
        for pg in context.pages:
            if "buildingconnected" in (pg.url or ""):
                page = pg
                break
        if not page:
            page = context.pages[0] if context.pages else await context.new_page()

        try:
            if "pipeline" not in (page.url or ""):
                await page.goto(PIPELINE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await asyncio.sleep(3)

            print(f"[INFO] URL: {page.url}")
            print(f"[INFO] Title: {await page.title()}")

            # 1) 找所有含 Undecided / Accepted / Declined 文本的可点击元素
            for kw in ["Undecided", "Accepted", "Declined", "Submitted", "Pending"]:
                try:
                    loc = page.get_by_text(kw, exact=False)
                    cnt = await loc.count()
                    print(f"\n[TAB-like] 含 \"{kw}\" 的元素数: {cnt}")
                    for i in range(min(cnt, 5)):
                        el = loc.nth(i)
                        try:
                            tag = await el.evaluate("el => el.tagName")
                            role = await el.get_attribute("role")
                            cls = await el.get_attribute("class")
                            txt = (await el.text_content() or "").strip()[:80]
                            print(f"  [{i}] <{tag}> role={role} class={(cls or '')[:60]} text={txt!r}")
                        except Exception as e:
                            print(f"  [{i}] (err: {e})")
                except Exception as e:
                    print(f"  lookup failed for {kw}: {e}")

            # 2) 尝试找项目列表行（常见结构：table row 或 div[role=row]）
            for sel in [
                "tr[data-row-key]", "tr[data-testid]", "tr[data-project-id]",
                "[role='row']", "[data-testid*='row' i]",
                "a[href*='/opportunities/']",
            ]:
                try:
                    n = await page.locator(sel).count()
                    if n > 0:
                        print(f"\n[ROW?] '{sel}' => {n} 个")
                        if n <= 30:
                            for i in range(min(n, 5)):
                                el = page.locator(sel).nth(i)
                                try:
                                    href = await el.get_attribute("href")
                                    txt = (await el.text_content() or "").strip()[:100]
                                    print(f"    [{i}] href={href} text={txt!r}")
                                except Exception:
                                    pass
                except Exception:
                    pass

            # 3) 保存整页 HTML + 截图，方便离线看
            html = await page.content()
            (DUMP_DIR / "pipeline.html").write_text(html, encoding="utf-8")
            try:
                await page.screenshot(path=str(DUMP_DIR / "pipeline.png"), full_page=True)
            except Exception as e:
                print(f"screenshot failed: {e}")

            # 4) 常见的左侧导航（folder 列表）
            for sel in ["nav a", "aside a", "[data-testid*='nav' i] a", "a[href*='pipeline']", "a[href*='folder']"]:
                try:
                    n = await page.locator(sel).count()
                    if 1 <= n <= 40:
                        print(f"\n[NAV] '{sel}' => {n} 个")
                        for i in range(min(n, 20)):
                            el = page.locator(sel).nth(i)
                            try:
                                href = await el.get_attribute("href")
                                txt = (await el.text_content() or "").strip()[:60]
                                if txt:
                                    print(f"    {txt!r}  ->  {href}")
                            except Exception:
                                pass
                except Exception:
                    pass

            print(f"\n[DUMP] HTML/截图保存到: {DUMP_DIR}/")
        finally:
            try:
                await browser.close()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
