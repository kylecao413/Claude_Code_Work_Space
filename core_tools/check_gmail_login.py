"""
检测 .env 中的 Gmail 凭证是否仍有效（仅 SMTP 登录，不发送邮件）。
"""
import os
import smtplib

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

def main():
    user = os.environ.get("GMAIL_USER", "").strip().strip('"')
    app_pass = os.environ.get("GMAIL_APP_PASS", "").strip().strip('"')

    if not user or not app_pass:
        print("错误：.env 中未配置 GMAIL_USER 或 GMAIL_APP_PASS。")
        return 1

    print(f"正在用 {user} 测试 SMTP 登录（不发送邮件）…")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(user, app_pass)
        print("结果：登录成功。当前 Gmail 应用专用密码有效。")
        return 0
    except smtplib.SMTPAuthenticationError as e:
        print("结果：登录失败（SMTP 认证错误）。")
        print("可能原因：")
        print("  1. 你改了 Google 账号密码，导致之前的「应用专用密码」被撤销")
        print("  2. 在 Google 账号里删除了该应用专用密码")
        print("建议：到 https://myaccount.google.com/apppasswords 重新生成一个应用专用密码，")
        print("      把 .env 里的 GMAIL_APP_PASS 换成新密码（注意保留空格）。")
        return 1
    except Exception as e:
        print("连接/登录出错：", e)
        return 1

if __name__ == "__main__":
    exit(main())
