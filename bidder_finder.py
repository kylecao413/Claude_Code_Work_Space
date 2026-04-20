"""
bidder_finder.py — 根据项目类型/预算/位置，找 DC 潜在投标 GC/Developer + POC 邮箱，用于 cold outreach。

Pipeline:
1. 用 constructionwire_dc_leads.py 抓 CW（或复用已有 leads.csv）
2. 按 --type / --min-budget / --max-budget 过滤
3. 从过滤后项目提取 developer_company + gc_company 公司名（去重）
4. 过滤：DC gov（§ 0-H）+ 已联系过（sent_log.csv + phone_log.csv 有 email_sent_date）
5. 并行 deep_search_contacts 找每家公司 POC（复用 batch_run_research._research_one_inproc）
6. 合并 phone_log.csv 里的电话
7. 输出 bidder_candidates_[slug]_[ts].json + .md

示例:
  python bidder_finder.py --type "office renovation" --min-budget 5 --max-budget 50 --pages 3
  python bidder_finder.py --type "hotel" --leads-csv leads.csv  # 复用已有 csv 跳过 scrape
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --- DC gov filter (copy from send_cw_outreach.py:137-149) ---
_GOV_DOMAINS = {"dc.gov", "wmata.com"}
_GOV_KEYWORDS = [
    "government of the district of columbia", "district of columbia",
    "dmped", "office of the deputy mayor", "department of general services",
    "department of buildings", "dc public schools", "dcps",
    "dc housing authority", "dcha", "wmata",
]


def is_gov_email(email: str) -> bool:
    if not email:
        return False
    return email.lower().split("@")[-1] in _GOV_DOMAINS


def is_gov_company(company: str) -> bool:
    if not company:
        return False
    c = company.lower()
    return any(kw in c for kw in _GOV_KEYWORDS)


# --- Dedup: 已联系过 ---
def load_already_contacted_emails() -> set[str]:
    emails: set[str] = set()
    sent_log = BASE_DIR / "sent_log.csv"
    if sent_log.exists():
        try:
            with sent_log.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    em = (row.get("contact_email") or "").strip().lower()
                    if em:
                        emails.add(em)
        except Exception as e:
            print(f"[WARN] sent_log.csv 读取失败: {e}", file=sys.stderr)

    phone_log = BASE_DIR / "phone_log.csv"
    if phone_log.exists():
        try:
            with phone_log.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    em = (row.get("email") or "").strip().lower()
                    sent = (row.get("email_sent_date") or "").strip()
                    if em and sent:  # 只算真正发过的
                        emails.add(em)
        except Exception as e:
            print(f"[WARN] phone_log.csv 读取失败: {e}", file=sys.stderr)
    return emails


def load_phone_map() -> dict:
    """email (lower) -> phone number，从 phone_log.csv 合并。"""
    phone_map: dict = {}
    phone_log = BASE_DIR / "phone_log.csv"
    if phone_log.exists():
        try:
            with phone_log.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    em = (row.get("email") or "").strip().lower()
                    ph = (row.get("phone") or "").strip()
                    if em and ph:
                        phone_map[em] = ph
        except Exception as e:
            print(f"[WARN] phone_log.csv 读取失败: {e}", file=sys.stderr)
    return phone_map


# --- Budget parsing ---
def _parse_budget_m(val: str):
    """'$15M' -> 15.0, '10' -> 10.0, '500K' -> 0.5, '$1.2B' -> 1200.0"""
    if not val:
        return None
    s = re.sub(r"[$,\s]", "", str(val).strip()).upper()
    if not s:
        return None
    mult = 1.0
    if s.endswith("B") or "BILLION" in s:
        s = re.sub(r"B$|BILLION.*", "", s).strip()
        mult = 1000.0
    elif s.endswith("M") or "MILLION" in s:
        s = re.sub(r"M$|MILLION.*", "", s).strip()
    elif s.endswith("K") or "THOUSAND" in s:
        s = re.sub(r"K$|THOUSAND.*", "", s).strip()
        mult = 0.001
    try:
        return float(s) * mult
    except ValueError:
        return None


# --- Filter leads ---
def filter_leads(leads, type_kw: str, min_m, max_m):
    out = []
    kw = (type_kw or "").lower().strip()
    for L in leads:
        # 关键词匹配 project_name（CW leads.csv 无独立 project_type 列，从 name 里搜）
        name = (L.get("project_name") or "").lower()
        if kw and kw not in name:
            continue
        v = _parse_budget_m(L.get("estimated_value", ""))
        if min_m is not None and (v is None or v < min_m):
            continue
        if max_m is not None and (v is None or v > max_m):
            continue
        out.append(L)
    return out


# --- Extract companies from filtered leads ---
def extract_companies(leads) -> dict:
    """{company_name: [{project, role, value}, ...]}，同一公司在多项目上出现会聚合。"""
    comp: dict = {}
    for L in leads:
        project = L.get("project_name", "")
        value = L.get("estimated_value", "")
        for role_key, role_name in [("developer_company", "Developer"), ("gc_company", "GC")]:
            c = (L.get(role_key) or "").strip()
            if c and not is_gov_company(c):
                comp.setdefault(c, []).append({
                    "project": project, "role": role_name, "value": value,
                })
    return comp


# --- CW scrape wrapper ---
def scrape_cw(pages: int, output_csv: Path) -> bool:
    cmd = [
        sys.executable,
        str(BASE_DIR / "constructionwire_dc_leads.py"),
        "--pages", str(pages),
        "--export", str(output_csv),
    ]
    print(f"Scraping CW (pages={pages})...", flush=True)
    r = subprocess.run(cmd, cwd=str(BASE_DIR), timeout=600)
    return r.returncode == 0 and output_csv.exists()


# --- Parallel deep search ---
def research_companies_parallel(companies, workers=5) -> dict:
    """{company_name: [contact_dicts]}，用 batch_run_research 的并行 worker。"""
    from batch_run_research import _research_one_inproc
    results: dict = {}
    print(f"\nResearching {len(companies)} companies (workers={workers})...", flush=True)
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_research_one_inproc, c): c for c in companies}
        for f in cf.as_completed(futures):
            company, ok, _output, contacts = f.result()
            results[company] = contacts if ok else []
            print(f"  {company}: {len(results[company])} POC", flush=True)
    return results


# --- Main ---
def main():
    ap = argparse.ArgumentParser(
        description="找 DC 潜在投标 GC/Developer + POC 邮箱（cold outreach target list）。"
    )
    ap.add_argument("--type", required=True,
                    help="项目类型关键词（匹配 project_name），例如 'office renovation' / 'hotel' / 'school'")
    ap.add_argument("--min-budget", type=float, default=None, help="最低估算金额（$M），例如 5 = $5M")
    ap.add_argument("--max-budget", type=float, default=None, help="最高估算金额（$M），例如 50 = $50M")
    ap.add_argument("--pages", type=int, default=3, help="CW 抓取页数（默认 3；复用 --leads-csv 时忽略）")
    ap.add_argument("--workers", type=int, default=5, help="并行 research worker 数（默认 5）")
    ap.add_argument("--leads-csv", default=None,
                    help="复用已有 CSV 跳过 CW 抓取（调试用）")
    ap.add_argument("--output-dir", default="Pending_Approval/Outbound",
                    help="输出目录（默认 Pending_Approval/Outbound）")
    args = ap.parse_args()

    # 1. Get leads
    if args.leads_csv:
        leads_csv = Path(args.leads_csv)
        if not leads_csv.is_absolute():
            leads_csv = BASE_DIR / leads_csv
        if not leads_csv.exists():
            print(f"leads CSV 不存在: {leads_csv}", file=sys.stderr)
            return 1
    else:
        ts_stamp = datetime.now().strftime("%Y%m%d_%H%M")
        leads_csv = BASE_DIR / f"_bidder_leads_{ts_stamp}.csv"
        if not scrape_cw(args.pages, leads_csv):
            print("CW 抓取失败或未产出 CSV。检查 cookies 和登录状态。", file=sys.stderr)
            return 1

    with leads_csv.open(encoding="utf-8") as f:
        leads = list(csv.DictReader(f))
    print(f"Loaded {len(leads)} leads from {leads_csv.name}", flush=True)

    # 2. Filter
    filtered = filter_leads(leads, args.type, args.min_budget, args.max_budget)
    budget_desc = f"{args.min_budget}M-{args.max_budget}M" if (args.min_budget or args.max_budget) else "any"
    print(f"Filtered: {len(filtered)} leads matched (type='{args.type}', budget={budget_desc})", flush=True)
    if not filtered:
        print("无匹配项目。放宽 --type/--min-budget/--max-budget 后重试。")
        return 1

    # 3. Extract companies
    companies = extract_companies(filtered)
    print(f"Extracted {len(companies)} unique companies (DC gov already excluded)", flush=True)
    if not companies:
        print("无非-DC-gov 公司。")
        return 1

    # 4. Load dedup sets
    already = load_already_contacted_emails()
    phone_map = load_phone_map()
    print(f"Already-contacted email pool: {len(already)}; phone-tracker entries: {len(phone_map)}",
          flush=True)

    # 5. Parallel POC research
    research_results = research_companies_parallel(sorted(companies.keys()), workers=args.workers)

    # 6. Build candidates
    candidates = []
    for company, contexts in companies.items():
        # 选估值最高的项目作为该公司 outreach context
        best_project = max(
            contexts,
            key=lambda x: _parse_budget_m(x.get("value", "")) or 0
        )
        contacts = research_results.get(company, [])
        if not contacts:
            continue  # 没找到 POC，跳过但不报错（DDGS 不稳定，预期部分失败）
        for c in contacts:
            em = (c.get("email") or "").strip().lower()
            if not em:
                # 无 email，不能用于冷邮件；可选：若 phone 可用，依然保留做电话外呼
                # v1 先只保留有 email 的（发 email 是主 channel）
                continue
            if em in already:
                continue
            if is_gov_email(em):
                continue
            candidates.append({
                "company": company,
                "poc_name": c.get("name", ""),
                "poc_role": c.get("role", ""),
                "email": em,
                "phone": phone_map.get(em, ""),
                "source_project": best_project["project"],
                "source_project_role": best_project["role"],
                "source_project_value": best_project["value"],
                "research_source": c.get("source", ""),
                "confidence": "high" if em and c.get("name") else "medium",
            })

    print(f"\nFinal candidates (dedup + gov filter): {len(candidates)}", flush=True)

    # 7. Output
    output_dir = BASE_DIR / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w]+", "_", args.type.strip())[:30].strip("_") or "bidders"
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    json_path = output_dir / f"bidder_candidates_{slug}_{ts}.json"
    md_path = output_dir / f"bidder_candidates_{slug}_{ts}.md"

    json_path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_lines = [
        f"# Bidder Candidates — {args.type}",
        "",
        f"**Generated**: {ts}  ",
        f"**Criteria**: type=`{args.type}`, budget={budget_desc}, pages={args.pages}  ",
        f"**Candidates**: {len(candidates)}  ",
        f"**Source leads**: `{leads_csv.name}` ({len(leads)} total, {len(filtered)} matched)",
        "",
        "---",
        "",
    ]
    if not candidates:
        md_lines.append("_No candidates. All POC were already-contacted, gov-filtered, or not found._")
    else:
        # 分组：有电话的优先展示（方便手动 SMS）
        with_phone = [c for c in candidates if c["phone"]]
        no_phone = [c for c in candidates if not c["phone"]]
        if with_phone:
            md_lines.append(f"## With Phone ({len(with_phone)}) — 可手动 SMS")
            md_lines.append("")
            for c in with_phone:
                md_lines.extend(_fmt_candidate_md(c))
        if no_phone:
            md_lines.append(f"## Email Only ({len(no_phone)}) — 只能 cold email")
            md_lines.append("")
            for c in no_phone:
                md_lines.extend(_fmt_candidate_md(c))

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\nOutputs:")
    print(f"  {json_path.relative_to(BASE_DIR)}")
    print(f"  {md_path.relative_to(BASE_DIR)}")
    return 0


def _fmt_candidate_md(c) -> list:
    return [
        f"### {c['company']} — {c['poc_name'] or '(unknown POC)'}",
        f"- **Email**: {c['email']}",
        f"- **Phone**: {c['phone'] or '_(not in tracker)_'}",
        f"- **POC Role**: {c['poc_role'] or '_(unknown)_'}",
        f"- **Source Project**: {c['source_project']} ({c['source_project_role']}, {c['source_project_value']})",
        f"- **Research Source**: {(c['research_source'] or '')[:100]}",
        f"- **Confidence**: {c['confidence']}",
        "",
    ]


if __name__ == "__main__":
    sys.exit(main())
