"""
ConstructionWire：自动登录（优先 Cookie）并抓取 DC 地区 Lead。
- 自动登录：优先加载 constructionwire_login 保存的 Cookie；若无或失效则提示先运行 constructionwire_login.py。
- 业务范围：DC、Northern VA、PG County、Montgomery County（.cursorrules 中 Inspection 地域）。
- 选择器基于你提供的 Search Projects / Project Details HTML 结构。
"""
import asyncio
import csv
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from playwright.async_api import async_playwright

from constructionwire_login import (
    COOKIES_PATH,
    has_saved_cookies,
    is_logged_in_url,
    LOGIN_URL,
)

# DC 地区 + “1–12 个月阶段” 搜索（与 “Search Projects DC 1 to 12 month stages Only” 一致）
BASE_URL = "https://www.constructionwire.com"
# rss=DC（州/地区）, pcstgs=3,4,5 为阶段筛选（如 Starts in 1-3 months, 4-12 months 等）, rtid=1 为报告类型
DC_SEARCH_URL = f"{BASE_URL}/Client/Report?rtid=1&rss=DC&pcstgs=3&pcstgs=4&pcstgs=5&p=1"


async def ensure_logged_in(page):
    """若当前 URL 已离开登录页则视为已登录。"""
    return is_logged_in_url(page.url)


async def open_dc_leads_section(page):
    """在已登录状态下打开 DC 地区 Lead 列表（1–12 个月阶段）。"""
    await page.goto(DC_SEARCH_URL, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=20000)
    # 等待结果表格出现
    await page.wait_for_selector("#search-results-grid tr[data-report-id]", timeout=15000)
    return page


def _parse_developer_and_gc(companies_cell: str) -> tuple[str, str]:
    """
    从列表页「公司」单元格解析 Developer 与 GC。
    ConstructionWire 前缀：(D)=Developer, (D/O)=Developer/Owner, (O)=Owner, (C)=Contractor/GC, (A)=Architect.
    """
    developer = ""
    gc = ""
    for line in (companies_cell or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        # 匹配开头 (D/O)、(D)、(O)、(C)、(A)，后面是公司名
        if line.startswith("(D/O)") and not developer:
            developer = line.replace("(D/O)", "").strip()
        elif line.startswith("(D)") and not developer:
            developer = line.replace("(D)", "").strip()
        elif line.startswith("(C)") and not gc:
            gc = line.replace("(C)", "").strip()
    return developer, gc


async def scrape_leads_from_current_page(page):
    """
    从当前搜索列表页解析 Lead。
    抓取：项目名称、估算金额、Developer 公司名、GC 公司名；联系人名字需在详情页获取（--details 时合并）。
    结构：tr[data-report-id] → td 顺序：checkbox, pin, title+address, stage/schedule, construction type, project type, value, companies, created/updated.
    """
    leads = []
    rows = page.locator("#search-results-grid tbody tr[data-report-id]")
    n = await rows.count()
    for i in range(n):
        row = rows.nth(i)
        report_id = await row.get_attribute("data-report-id") or ""

        # 项目名称与详情链接
        title_el = row.locator("td a.title").first
        title = (await title_el.text_content() or "").strip()
        detail_href = await title_el.get_attribute("href") or ""

        # 地址与地点
        addr1 = await row.locator("span.address1").first.text_content()
        address1 = (addr1 or "").strip()
        city_el = row.locator("span.city").first
        state_el = row.locator("span.state").first
        zip_el = row.locator("span.postal-code").first
        city = (await city_el.text_content() or "").strip()
        state = (await state_el.text_content() or "").strip()
        postal = (await zip_el.text_content() or "").strip()

        # 阶段与工期
        stage_el = row.locator("span.construction-stage").first
        schedule_el = row.locator("span.construction-schedule").first
        stage = (await stage_el.text_content() or "").strip()
        schedule = (await schedule_el.text_content() or "").strip().replace("\n", " ")

        # 第 4–8 列：construction type, project type, value, companies, dates
        tds = row.locator("td")
        construction_type = ""
        project_type = ""
        value = ""
        companies_cell = ""
        dates_cell = ""
        if await tds.count() >= 9:
            construction_type = (await tds.nth(4).text_content() or "").strip()
            project_type = (await tds.nth(5).text_content() or "").strip()
            value = (await tds.nth(6).text_content() or "").strip()
            companies_cell = (await tds.nth(7).text_content() or "").strip()
            dates_cell = (await tds.nth(8).text_content() or "").strip()

        developer_company, gc_company = _parse_developer_and_gc(companies_cell)

        leads.append({
            "report_id": report_id,
            "project_name": title,
            "title": title,
            "estimated_value": value,
            "value": value,
            "developer_company": developer_company,
            "gc_company": gc_company,
            "contact_names": [],
            "detail_url": detail_href if detail_href.startswith("http") else (BASE_URL + detail_href) if detail_href else "",
            "address": address1,
            "city": city,
            "state": state,
            "postal_code": postal,
            "stage": stage,
            "schedule": schedule,
            "construction_type": construction_type,
            "project_type": project_type,
            "companies": companies_cell,
            "created_updated": dates_cell,
        })
    return leads


async def scrape_detail_page(page, detail_url: str) -> dict:
    """
    打开一条 Lead 的详情页并解析（基于 Project Details / Opened Lead Project Detail Page HTML）。
    返回单条增强信息：location 全文、stage、estimated_value、contacts 等。
    """
    if not detail_url:
        return {}
    await page.goto(detail_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=15000)

    data = {}
    # 标题
    title_el = page.locator("div.report-heading .title, div.report .title").first
    data["title"] = (await title_el.text_content() or "").strip()

    # Location（Project Information 表内）
    loc_td = page.locator("td.field-value:has(span.city)").first
    data["location_full"] = (await loc_td.text_content() or "").strip()

    # Estimated Schedule 表：Stage, Construction Start/End
    schedule_tbody = page.locator("tbody.schedule")
    if await schedule_tbody.count():
        rows = schedule_tbody.locator("tr")
        for r in range(await rows.count()):
            label = await rows.nth(r).locator("td.field").text_content()
            if label and "Stage:" in (label or ""):
                data["stage"] = (await rows.nth(r).locator("td.field-value").text_content() or "").strip()
            if label and "Construction Start:" in (label or ""):
                data["construction_start"] = (await rows.nth(r).locator("td.field-value").text_content() or "").strip()
            if label and "Construction End:" in (label or ""):
                data["construction_end"] = (await rows.nth(r).locator("td.field-value").text_content() or "").strip()

    # Contact Information 表：tr[data-contact-id]；提取联系人名字（Contact 列中第一个 span 或首行）
    contacts = []
    for contact_row in await page.locator("tbody.contact-info tr[data-contact-id]").all():
        role = (await contact_row.locator("td").nth(0).text_content() or "").strip()
        company_cell = await contact_row.locator("td").nth(1).text_content()
        company = (company_cell or "").strip()
        contact_cell = await contact_row.locator("td").nth(2).text_content()
        contact = (contact_cell or "").strip()
        name_el = contact_row.locator("td").nth(2).locator("span").first
        contact_name = (await name_el.text_content() or "").strip() if await name_el.count() else (contact.split("\n")[0].strip() if contact else "")
        email_el = contact_row.locator("a[href^='mailto:']").first
        email = await email_el.get_attribute("href")
        if email and email.startswith("mailto:"):
            email = email.replace("mailto:", "").strip()
        else:
            email = ""
        contacts.append({"role": role, "company": company, "contact": contact, "name": contact_name, "email": email})
    data["contacts"] = contacts

    return data


def _export_leads_csv(leads: list, path: str) -> None:
    """将 Lead 列表导出为 leads.csv，供 batch_run_research 等使用。"""
    if not leads:
        return
    fieldnames = [
        "report_id", "project_name", "stage", "estimated_value",
        "developer_company", "gc_company", "address", "city", "state", "postal_code",
        "detail_url", "contact_names",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for lead in leads:
            row = {k: lead.get(k, "") for k in fieldnames}
            if isinstance(row.get("contact_names"), list):
                row["contact_names"] = "; ".join(str(x) for x in row["contact_names"])
            w.writerow(row)
    print(f"已导出 {len(leads)} 条 Lead 到 {path}")


async def run(headless: bool = False, max_pages: int = 1, scrape_details: bool = False, export_path: str | None = None):
    if not has_saved_cookies():
        print("未检测到已保存的登录状态。请先运行： python constructionwire_login.py")
        return 1

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            storage_state=COOKIES_PATH,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=15000)

            if not await ensure_logged_in(page):
                print("Cookie 已失效，请先运行： python constructionwire_login.py")
                return 1

            await open_dc_leads_section(page)
            all_leads = []
            for pagenum in range(1, max_pages + 1):
                if pagenum > 1:
                    next_url = DC_SEARCH_URL.replace("p=1", f"p={pagenum}")
                    await page.goto(next_url, wait_until="domcontentloaded")
                    await page.wait_for_load_state("networkidle", timeout=20000)
                leads = await scrape_leads_from_current_page(page)
                all_leads.extend(leads)
                print(f"第 {pagenum} 页解析到 {len(leads)} 条 Lead。")
                if not leads:
                    break

            print(f"合计 {len(all_leads)} 条 Lead。")
            if export_path:
                _export_leads_csv(all_leads, export_path)
            if scrape_details and all_leads:
                for i, lead in enumerate(all_leads[:3]):  # 仅前 3 条做详情，避免过慢
                    extra = await scrape_detail_page(page, lead.get("detail_url") or "")
                    lead["detail"] = extra
                    lead["contact_names"] = [c.get("name") or (c.get("contact", "").split("\n")[0].strip()) for c in extra.get("contacts", [])]
                    print(f"  详情 [{i+1}] {lead.get('project_name', '')[:50]}… contacts={len(extra.get('contacts', []))} names={lead['contact_names']}")

            # 调试时可暂停
            if not headless:
                await page.pause()
        finally:
            await browser.close()

    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="ConstructionWire DC 地区 Lead 抓取")
    ap.add_argument("--headless", action="store_true", help="无头模式")
    ap.add_argument("--pages", type=int, default=1, help="抓取页数（默认 1）")
    ap.add_argument("--details", action="store_true", help="对前几条抓取详情页（联系人等）")
    ap.add_argument("--export", dest="export_path", default=None, help="导出为 CSV，如 leads.csv")
    args = ap.parse_args()
    sys.exit(asyncio.run(run(
        headless=args.headless,
        max_pages=args.pages,
        scrape_details=args.details,
        export_path=args.export_path,
    )))


if __name__ == "__main__":
    main()
