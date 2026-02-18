"""
从 admin@buildingcodeconsulting.com 发送邮件，抄送 ycao@buildingcodeconsulting.com。
用于 Inspection/Plan Review 正式开发信，不追加签名（账号已带签名）。
使用 Private Email (PRIV_MAIL1_*) 的 SMTP，确保发件显示为 admin@ 且出现在 Private Email 已发送。
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

ADMIN_FROM = "admin@buildingcodeconsulting.com"
CC_YCAO = "ycao@buildingcodeconsulting.com"


def send_from_admin(to_email: str, subject: str, body_plain: str, cc: str | None = None) -> tuple[bool, str]:
    """
    使用 admin@ (Private Email PRIV_MAIL1_*) 发送邮件，默认抄送 ycao@。
    :return: (success, message)
    """
    user = os.environ.get("PRIV_MAIL1_USER", "").strip().strip('"')
    password = os.environ.get("PRIV_MAIL1_PASS", "").strip().strip('"')
    smtp_host = os.environ.get("PRIV_MAIL1_SMTP", "smtp.privateemail.com").strip().strip('"')
    if not user or not password:
        return False, "请在 .env 中配置 PRIV_MAIL1_USER 和 PRIV_MAIL1_PASS（admin@ 的 Private Email 密码）。"

    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e != CC_YCAO and e != to_email:
                cc_list.append(e)

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Cc"] = ", ".join(cc_list)
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, 587) as server:
            server.starttls()
            server.login(user, password)
            recipients = [to_email] + cc_list
            server.sendmail(user, recipients, msg.as_string())
        return True, f"已从 {user} 发送至 {to_email}，抄送 {', '.join(cc_list)}"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP 认证失败: {e}"
    except Exception as e:
        return False, str(e)


def send_from_admin_with_attachment(
    to_email: str,
    subject: str,
    body_plain: str,
    attachment_path: str,
    cc: str | None = None,
) -> tuple[bool, str]:
    """
    使用 admin@ 发送带 PDF 附件的邮件，默认抄送 ycao@。
    :param attachment_path: 本地 PDF 文件的绝对路径
    :return: (success, message)
    """
    user = os.environ.get("PRIV_MAIL1_USER", "").strip().strip('"')
    password = os.environ.get("PRIV_MAIL1_PASS", "").strip().strip('"')
    smtp_host = os.environ.get("PRIV_MAIL1_SMTP", "smtp.privateemail.com").strip().strip('"')
    if not user or not password:
        return False, "请在 .env 中配置 PRIV_MAIL1_USER 和 PRIV_MAIL1_PASS。"

    if not os.path.isfile(attachment_path):
        return False, f"附件文件不存在: {attachment_path}"

    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e != CC_YCAO and e != to_email:
                cc_list.append(e)

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Cc"] = ", ".join(cc_list)
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))

    # Attach PDF
    filename = os.path.basename(attachment_path)
    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, 587) as server:
            server.starttls()
            server.login(user, password)
            recipients = [to_email] + cc_list
            server.sendmail(user, recipients, msg.as_string())
        return True, f"已从 {user} 发送至 {to_email}（附件: {filename}），抄送 {', '.join(cc_list)}"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP 认证失败: {e}"
    except Exception as e:
        return False, str(e)
