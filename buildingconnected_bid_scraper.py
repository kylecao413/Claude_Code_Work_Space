"""
BuildingConnected Bid 抓取：登录 BC，检索 Washington DC 近 2–3 个月投标邀请，
列出项目并标记是否已提交提案。使用 Playwright，Cookie 保存到 .buildingconnected_cookies.json。
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
COOKIES_PATH = BASE_DIR / ".buildingconnected_cookies.json"
# BuildingConnected 典型 URL（需根据实际站点调整）
BC_BASE = "https://app.buildingconnected.com"
BC_LOGIN = "https://accounts.buildingconnected.com"  # 或 BC 实际登录页
# DC 项目筛选：通常通过地区 Washington DC 与日期筛选
DC_FILTER = "Washington, DC"  # 或 "Washington DC", "District of Columbia"


async def ensure_logged_in(page) -> bool:
    """若当前 URL 不在登录页则视为已登录。"""
    url = page.url.lower()
    return "login" not in url and "signin" not in url and "accounts." not in url


async def open_bid_invites_dc(page, months_back: int = 3):
    """
    在 BuildingConnected 中打开 Bid Invites 列表并筛选 Washington DC、近 N 个月。
    具体路径与参数需根据实际 BC 界面调整（可从 St. Joseph's 等保存的 HTML 反推）。
    """
    # 示例：先进入项目/投标列表页
    await page.goto(f"{BC_BASE}/projects", wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=15000)
    # TODO: 在页面上选择地区 DC、时间范围、Bid Invite 类型（需根据实际 DOM 选择器调整）
    # 例如: await page.click('text=Washington DC'); await page.click('text=Bid Invites');
    return page


def _parse_project_row(row_el) -> dict:
    """从列表行解析项目信息（选择器需按实际 BC 列表结构调整）。"""
    # 占位：实际需从 St. Joseph's 等 HTML 或 live 页面获取 class/data 属性
    return {
        "name": "",
        "client": "",
        "location": "",
        "bid_due_date": "",
        "submitted": False,
        "detail_url": "",
    }


async def scrape_bid_list(page) -> list[dict]:
    """从当前页面抓取 Bid Invite 列表。"""
    projects = []
    # 常见模式：表格或卡片列表，带 project name / client / location / date
    rows = page.locator("[data-testid='project-row'], .project-row, table tbody tr")
    n = await rows.count()
    for i in range(n):
        row = rows.nth(i)
        try:
            item = await _parse_project_row(row)
            if item.get("name"):
                projects.append(item)
        except Exception:
            continue
    return projects


async def scrape_project_detail(page, detail_url: str) -> dict:
    """
    打开项目详情页，抓取描述、规模、用途变更、检测范围（Building, MEP, Fire）、
    Permit Set / 设计文档链接等。可选：下载 Permit Set 到 ../Projects/[Client]/[Project]/。
    """
    if not detail_url:
        return {}
    await page.goto(detail_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=15000)
    detail = {
        "description": "",
        "size_sqft": "",
        "change_of_use": "",
        "scope_building": False,
        "scope_mep": False,
        "scope_fire": False,
        "permit_set_links": [],
        "index_notes": "",
    }
    # TODO: 根据实际详情页 DOM 用 page.locator 提取上述字段
    body = await page.locator("body").inner_text()
    detail["description"] = body[:5000]
    return detail


async def run(headless: bool = False, months_back: int = 3, max_projects: int = 20):
    """
    主流程：加载 Cookie 或要求登录 → 打开 DC Bid Invites → 抓取列表 →
    可选抓取每项详情。返回 { "projects": [...], "not_submitted": [...] }。
    """
    if COOKIES_PATH.exists():
        try:
            with open(COOKIES_PATH, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except Exception:
            storage = None
    else:
        storage = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        )
        if storage:
            await context.add_cookies(storage.get("cookies", []))
        page = await context.new_page()

        try:
            await page.goto(BC_BASE, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=15000)
            if not await ensure_logged_in(page):
                print("未检测到登录状态。请在打开的浏览器中登录 BuildingConnected，登录成功后按 Enter 继续。")
                if not headless:
                    await page.pause()
                await page.wait_for_load_state("networkidle", timeout=60000)
            if not await ensure_logged_in(page):
                print("仍未登录，请重新运行并完成登录。")
                await browser.close()
                return []

            # 保存 Cookie 供下次使用
            state = await context.storage_state()
            with open(COOKIES_PATH, "w", encoding="utf-8") as f:
                json.dump({"cookies": state.get("cookies", [])}, f, indent=2)
            print("已保存 Cookie 到", COOKIES_PATH)

            await open_bid_invites_dc(page, months_back=months_back)
            projects = await scrape_bid_list(page)
            not_submitted = [p for p in projects if not p.get("submitted")]
            print(f"共 {len(projects)} 个 DC Bid Invite，其中 {len(not_submitted)} 个尚未提交提案。")
            if not_submitted:
                for i, p in enumerate(not_submitted[:max_projects], 1):
                    print(f"  {i}. {p.get('name', 'N/A')} | {p.get('client', '')} | {p.get('location', '')}")
            await browser.close()
            return {"projects": projects, "not_submitted": not_submitted}
        except Exception as e:
            print("运行出错:", e)
            await browser.close()
            return {"projects": [], "not_submitted": []}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="BuildingConnected DC Bid Invites 抓取")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--months", type=int, default=3, help="回溯月数")
    ap.add_argument("--max", type=int, default=20, help="最多列出未提交数量")
    args = ap.parse_args()
    result = asyncio.run(run(headless=args.headless, months_back=args.months, max_projects=args.max))
    sys.exit(0 if result.get("not_submitted") is not None else 1)


if __name__ == "__main__":
    main()
