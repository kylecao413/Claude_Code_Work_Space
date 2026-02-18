"""
任务完成提醒：Cursor 完成 Inbox/ACTIVE_TASK.md 中的任务并更新 TASK_STATUS.md 后，可运行本脚本发出提示音。
Windows: 使用 winsound；其他系统: 终端 \a 或跳过。
"""
import sys

def main():
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        winsound.Beep(880, 200)
        winsound.Beep(1100, 200)
    except Exception:
        try:
            print("\a\a", end="", flush=True)
        except Exception:
            pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
