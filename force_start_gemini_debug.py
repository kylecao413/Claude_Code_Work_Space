"""
纯净模式启动 Chrome：先清理所有 Chrome 进程，再用独立 profile + 调试端口 9222 启动，
避免「后台驻留」或路径/引号问题导致端口开不了。
运行后在新窗口登录 Gemini，再执行：python google_gemini_login_chrome.py
"""
import os
import subprocess
import time

# Chrome 常见安装路径
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def hard_reset_chrome():
    print("正在强行清理所有 Chrome 进程...")
    os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
    time.sleep(2)

    chrome_path = None
    for p in CHROME_PATHS:
        if os.path.isfile(p):
            chrome_path = p
            break
    if not chrome_path:
        print("未找到 Chrome，请确认已安装并修改脚本中的路径。")
        return

    # 独立临时数据目录，不受日常 Profile 干扰
    user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_debug_profile")

    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "https://gemini.google.com",
    ]

    print("正在以调试模式启动全新 Chrome...")
    subprocess.Popen(cmd)
    print("请在弹出的浏览器中登录 Gemini。登录完成后，回到终端运行：")
    print("  python google_gemini_login_chrome.py")


if __name__ == "__main__":
    hard_reset_chrome()
