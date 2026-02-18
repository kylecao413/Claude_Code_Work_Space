"""
BuildingConnected 单项目全流程演示：
1) 使用 St. Joseph's on Capitol Hill – Phase I 作为示例项目；
2) 打印定价摘要表供确认；
3) 生成提案 Word 到 ../Projects/[Client]/[Project]/；
4) 在 Pending_Approval/Outbound/ 创建邮件草稿。
若已配置 BuildingConnected Cookie，可先运行 buildingconnected_bid_scraper 取真实项目再传入。
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from proposal_generator import run_single_project

# 示例项目（与 St. Joseph's 一致；可从 BC 抓取结果替换）
DEMO_PROJECT = {
    "name": "St. Joseph's on Capitol Hill – Phase I",
    "client": "St. Joseph's / Owner",
    "description": "Phase I renovation; DC; scope includes building, MEP, and fire protection review.",
    "is_repeat": False,
    "is_key_account": False,
}


def main():
    print("BuildingConnected 提案流程演示 – 示例项目:", DEMO_PROJECT["name"])
    # skip_confirm=False 会打印定价表；若需无交互直接生成可设 True 并传入 --yes
    skip = "--yes" in sys.argv or "-y" in sys.argv
    result = run_single_project(DEMO_PROJECT, price_per_visit=None, est_visits=12, skip_confirm=skip)
    if result["success"]:
        print("\n✅ 提案与邮件草稿已生成。请审阅后可将草稿改名为 XXX-OK.md 发送。")
    else:
        print("❌", result.get("error"), file=sys.stderr)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
