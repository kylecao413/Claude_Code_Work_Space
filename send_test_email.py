"""
从 Gmail 发送测试邮件到 admin@buildingcodeconsulting.com，用于验证 SMTP 连接。
所有凭据从 .env 读取，不硬编码密码。
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 从脚本所在目录加载 .env
try:
    from dotenv import load_dotenv
    import os as _os
    _env_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass  # 无 dotenv 时依赖系统环境变量

def main():
    user = os.environ.get("GMAIL_USER", "").strip().strip('"')
    app_pass = os.environ.get("GMAIL_APP_PASS", "").strip().strip('"')

    if not user or not app_pass or "your-gmail" in user or "你的" in app_pass:
        print("错误：请在 .env 中配置有效的 GMAIL_USER 和 GMAIL_APP_PASS（谷歌应用专用密码）。")
        return 1

    to_addr = "admin@buildingcodeconsulting.com"
    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to_addr
    msg["Subject"] = "Test Email – Building Code Consulting Automation"

    body = (
        "This is a test email from the Business Automation environment.\n\n"
        "If you received this, Gmail SMTP connection is working.\n\n"
        "— Kyle Cao (PE, MCP)"
    )
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(user, app_pass)
            server.sendmail(user, to_addr, msg.as_string())
        print("测试邮件已成功发送至 admin@buildingcodeconsulting.com")
        return 0
    except smtplib.SMTPAuthenticationError as e:
        print("SMTP 认证失败（请检查 Gmail 应用专用密码与两步验证）：", e)
        return 1
    except Exception as e:
        print("发送失败：", e)
        return 1

if __name__ == "__main__":
    exit(main())
