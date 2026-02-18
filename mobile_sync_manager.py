"""
手机端指令执行器：实时监听 Pending_Approval（含 Outbound/、Replies/），检测到 -OK 立即发送；
监听 Carr_Properties_FollowUp.txt，将 Called-NoAnswer 等纳入下周一重播清单；
每日下午 5 点向 ycao@ 发送今日进度简报。
"""
import os
import re
import time
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

from approval_monitor import scan_and_process, PENDING_DIR, SENT_DIR
from email_sender import send_from_admin

BASE_DIR = Path(__file__).resolve().parent
CARR_FOLLOWUP = BASE_DIR / "Carr_Properties_FollowUp.txt"
NEXT_MONDAY_REPLAY = BASE_DIR / "next_monday_replay.txt"
CC_YCAO = "ycao@buildingcodeconsulting.com"
SUMMARY_TO = CC_YCAO


def process_carr_followup():
    """读取 Carr_Properties_FollowUp.txt，将标记为 Called-NoAnswer 等项加入下周一重播清单。"""
    if not CARR_FOLLOWUP.exists():
        return
    text = CARR_FOLLOWUP.read_text(encoding="utf-8")
    lines = text.splitlines()
    added = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "Called-NoAnswer" in line or "NoAnswer" in line or "no answer" in line.lower():
            added.append(line)
    if not added:
        return
    NEXT_MONDAY_REPLAY.parent.mkdir(parents=True, exist_ok=True)
    with open(NEXT_MONDAY_REPLAY, "a", encoding="utf-8") as f:
        f.write(f"\n# 添加于 {datetime.now().isoformat()}\n")
        for a in added:
            f.write(a + "\n")
    print(f"  [Carr] 已将 {len(added)} 条加入下周一重播清单: {NEXT_MONDAY_REPLAY.name}")


def send_daily_summary():
    """汇总今日进度并发送到 ycao@。"""
    pending_count = 0
    sent_today = 0
    replies_count = 0
    if PENDING_DIR.exists():
        pending_count = len(list(PENDING_DIR.rglob("*.md"))) - len(list(PENDING_DIR.rglob("*-OK.md")))
        replies_count = len(list((PENDING_DIR / "Replies").glob("*.md"))) if (PENDING_DIR / "Replies").exists() else 0
    if SENT_DIR.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        for f in SENT_DIR.glob("*.md"):
            try:
                if f.stat().st_mtime and datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d") == today:
                    sent_today += 1
            except Exception:
                pass
    body = (
        f"Building Code Consulting 今日进度简报\n"
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"- 待审批草稿数: {pending_count}\n"
        f"- 今日已发送: {sent_today}\n"
        f"- 待审批回复草稿(Replies): {replies_count}\n\n"
        f"请审阅 Pending_Approval 下草稿，将需发送的改名为 XXX-OK.md 后由监控脚本发送。\n"
    )
    ok, msg = send_from_admin(SUMMARY_TO, "BCC 今日进度简报", body)
    if ok:
        print(f"  [简报] 已发送至 {SUMMARY_TO}")
    else:
        print(f"  [简报] 发送失败: {msg}")


def run_loop(scan_interval_sec: int = 30, summary_hour: int = 17):
    """主循环：扫描 -OK、处理 Carr 跟进、每日 17:00 简报。"""
    last_summary_date = None
    while True:
        scan_and_process()
        process_carr_followup()
        now = datetime.now()
        if now.hour == summary_hour and (last_summary_date is None or last_summary_date != now.date()):
            send_daily_summary()
            last_summary_date = now.date()
        time.sleep(scan_interval_sec)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="手机端监控：-OK 发送、Carr 重播清单、每日 17:00 简报")
    ap.add_argument("--once", action="store_true", help="仅执行一次审批扫描 + Carr 处理后退出")
    ap.add_argument("--summary-now", action="store_true", help="立即发送一次今日简报")
    ap.add_argument("--interval", type=int, default=30, help="扫描间隔秒数，默认 30")
    ap.add_argument("--summary-hour", type=int, default=17, help="每日简报小时，默认 17")
    args = ap.parse_args()

    if args.summary_now:
        send_daily_summary()
        return
    if args.once:
        scan_and_process()
        process_carr_followup()
        return

    print(f"手机端监控已启动：每 {args.interval} 秒扫描 -OK；每日 {args.summary_hour}:00 发送简报。Ctrl+C 退出。")
    run_loop(scan_interval_sec=args.interval, summary_hour=args.summary_hour)


if __name__ == "__main__":
    main()
