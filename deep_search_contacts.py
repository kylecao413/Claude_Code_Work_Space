"""
深度搜索关键联系人（AI 辅助）。
拿到公司名（如某 GC/Developer）后，通过网页搜索 + AI 推断，寻找 2–5 个适合谈 Plan Review / Inspection 合作的负责人及邮箱。
支持：Gemini API（.env 中 GEMINI_API_KEY）提炼联系人；无 API 时仅做网页搜索并尝试从摘要中提取邮箱。
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# 网页搜索：优先 duckduckgo-search，无则退化为占位
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

# Gemini：用于从搜索结果中推断联系人与邮箱
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"')


def _search_web(company: str, max_results: int = 15) -> List[dict]:
    """对该公司做多组搜索，返回标题+摘要列表。"""
    if not HAS_DDGS:
        return []
    results = []
    queries = [
        f"{company} Project Manager",
        f"{company} Principal construction",
        f"{company} key contacts Plan Review Inspection DC",
    ]
    with DDGS() as ddgs:
        for q in queries:
            for r in ddgs.text(q, max_results=5):
                results.append({"title": r.get("title", ""), "body": r.get("body", "")})
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
    return results


def _extract_emails_from_text(text: str) -> List[str]:
    """从文本中提取邮箱。"""
    if not text:
        return []
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(dict.fromkeys(re.findall(pattern, text)))


def _infer_contacts_with_gemini(company: str, search_results: List[dict], max_contacts: int = 5) -> List[dict]:
    """用 Gemini 从搜索结果中推断 2–5 个关键联系人及邮箱。"""
    if not GEMINI_API_KEY or not search_results:
        return []
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        print(f"Gemini 初始化失败: {e}", file=sys.stderr)
        return []

    combined = "\n\n".join(
        f"[{i+1}] {r.get('title', '')}\n{r.get('body', '')}" for i, r in enumerate(search_results)
    )
    prompt = f"""你正在为 Building Code Consulting（Plan Review 与 Inspection 业务）寻找合作联系人。

公司名：{company}

以下是从网络搜索得到的与该公司相关的片段：

{combined[:28000]}

请从上述内容中推断并列出 2 到 {max_contacts} 位最适合洽谈 Plan Review 和 Inspection 合作的负责人（如 Project Manager、Principal、Director of Construction 等）。
对每位联系人请给出：
1. name（姓名）
2. role（职位/角色，若可推断）
3. email（若片段中出现或可合理推断的邮箱，否则留空）
4. source（简短依据，如来自哪条片段或推断理由）

以 JSON 数组格式回复，且只输出 JSON，不要其他说明。示例：
[{{"name": "Jane Doe", "role": "Project Manager", "email": "jane@company.com", "source": "片段2"}}]
"""
    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        # 取 JSON 部分（去除 markdown 代码块）
        if "```" in text:
            text = re.sub(r"^```\w*\n?", "", text).strip()
            text = re.sub(r"\n?```\s*$", "", text).strip()
        arr = json.loads(text)
        if isinstance(arr, list):
            return arr[:max_contacts]
        return []
    except Exception as e:
        print(f"Gemini 解析失败: {e}", file=sys.stderr)
        return []


def _fallback_contacts_from_snippets(company: str, search_results: List[dict], max_contacts: int = 5) -> List[dict]:
    """无 Gemini 时：从摘要中提取邮箱，并尽量保留标题/片段中的名字。"""
    contacts = []
    seen_emails = set()
    for r in search_results:
        body = (r.get("body") or "") + " " + (r.get("title") or "")
        emails = _extract_emails_from_text(body)
        for e in emails:
            if e in seen_emails:
                continue
            seen_emails.add(e)
            contacts.append({
                "name": "",
                "role": "（从网页摘要推断）",
                "email": e,
                "source": (r.get("title") or "")[:80],
            })
            if len(contacts) >= max_contacts:
                return contacts
    return contacts


def deep_search_contacts(
    company_name: str,
    max_contacts: int = 5,
    use_gemini: bool = True,
) -> List[dict]:
    """
    对给定公司进行深度搜索，返回 2–5 个关键联系人（姓名、角色、邮箱）。
    任务话术：寻找最适合谈 Plan Review 和 Inspection 合作的 Point of Contact。
    """
    if not company_name or not company_name.strip():
        return []

    company = company_name.strip()
    search_results = _search_web(company, max_results=15)

    if not search_results:
        print("未获取到网页搜索结果；若需搜索请安装: pip install duckduckgo-search", file=sys.stderr)
        return []

    if use_gemini and GEMINI_API_KEY:
        contacts = _infer_contacts_with_gemini(company, search_results, max_contacts)
    else:
        contacts = _fallback_contacts_from_snippets(company, search_results, max_contacts)

    return contacts


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="深度搜索公司关键联系人（Plan Review / Inspection 合作），支持 Gemini 推断邮箱。"
    )
    ap.add_argument("company", nargs="?", help="公司名（如 GC 或 Developer 名称）")
    ap.add_argument("--max", type=int, default=5, help="最多返回几名联系人（默认 5）")
    ap.add_argument("--no-gemini", action="store_true", help="不使用 Gemini，仅从网页摘要提取邮箱")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    company = args.company or os.environ.get("DEEP_SEARCH_COMPANY", "").strip()
    if not company:
        print("请提供公司名：deep_search_contacts.py 'Gilbane, Inc.' 或在 .env 中设置 DEEP_SEARCH_COMPANY", file=sys.stderr)
        sys.exit(1)

    contacts = deep_search_contacts(company, max_contacts=args.max, use_gemini=not args.no_gemini)

    if args.json:
        print(json.dumps(contacts, ensure_ascii=False, indent=2))
    else:
        print(f"公司: {company}")
        print(f"找到 {len(contacts)} 位联系人（适合 Plan Review / Inspection 合作）：\n")
        for i, c in enumerate(contacts, 1):
            print(f"  {i}. {c.get('name') or '(未识别)'} — {c.get('role', '')}")
            if c.get("email"):
                print(f"     Email: {c['email']}")
            if c.get("source"):
                print(f"     依据: {c['source'][:70]}…")
            print()

    sys.exit(0 if contacts else 1)


if __name__ == "__main__":
    main()
