"""
Send emails from admin@buildingcodeconsulting.com (or ycao@), CC ycao@.
Sends HTML email with inline BCC logo + professional signature block.
Signature adapts to the sending address automatically.
"""
import base64
import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

try:
    from dotenv import load_dotenv
    _dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_dir, ".env"))
except ImportError:
    pass

ADMIN_FROM = "admin@buildingcodeconsulting.com"
CC_YCAO    = "ycao@buildingcodeconsulting.com"

# ── Signature ─────────────────────────────────────────────────────────────────
LOGO_PATH = Path(__file__).resolve().parent.parent / "Marketing" / "Business Card BCC Kevin C..png"

_SIG_NAME  = "Kevin C., PE, MCP"
_SIG_TITLE = "Professional In Charge/President"
_SIG_CO    = "Building Code Consulting LLC"
_SIG_CELL  = "(571) 365-6937"

def _sig_email(from_addr: str) -> str:
    """Return the email shown in the signature based on sending address."""
    addr = from_addr.lower().strip()
    if "ycao" in addr:
        return CC_YCAO
    return ADMIN_FROM


def _signature_plain(from_addr: str) -> str:
    return (
        f"\n\n--\n"
        f"{_SIG_NAME}\n"
        f"{_SIG_TITLE}\n"
        f"{_SIG_CO}\n"
        f"Cell: {_SIG_CELL}\n"
        f"{_sig_email(from_addr)}"
    )


def _signature_html(from_addr: str) -> str:
    email_line = _sig_email(from_addr)
    logo_cid = "bcc_logo_sig"
    return f"""
<table cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;">
  <tr>
    <td style="font-family:Arial,sans-serif;font-size:10pt;color:#222;line-height:1.6;">
      <strong>{_SIG_NAME}</strong><br>
      {_SIG_TITLE}<br>
      {_SIG_CO}<br>
      Cell: {_SIG_CELL}<br>
      <a href="mailto:{email_line}" style="color:#1a73e8;text-decoration:none;">{email_line}</a>
    </td>
  </tr>
  <tr>
    <td style="padding-top:8px;">
      <img src="cid:{logo_cid}" alt="BCC Logo" style="max-width:240px;height:auto;">
    </td>
  </tr>
</table>
"""


def _build_html_message(
    from_addr: str,
    to_email: str,
    subject: str,
    body_plain: str,
    cc_list: list[str],
    attachment_path: str | None = None,
) -> MIMEMultipart:
    """
    Build a multipart/related HTML email with:
      - Plain text fallback
      - HTML body with proper signature block
      - Inline BCC logo (cid:bcc_logo_sig)
      - Optional PDF attachment
    """
    # Outer container: related (holds html + inline image)
    outer = MIMEMultipart("related")
    outer["From"]    = from_addr
    outer["To"]      = to_email
    outer["Subject"] = subject
    outer["Cc"]      = ", ".join(cc_list)

    # Alternative: plain + html
    alt = MIMEMultipart("alternative")
    outer.attach(alt)

    # Plain text version (body + text signature)
    plain_full = body_plain + _signature_plain(from_addr)
    alt.attach(MIMEText(plain_full, "plain", "utf-8"))

    # HTML version
    body_html = body_plain.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html_full = f"""<html><body>
<p style="font-family:Arial,sans-serif;font-size:11pt;color:#222;line-height:1.7;max-width:620px;">
{body_html}
</p>
{_signature_html(from_addr)}
</body></html>"""
    alt.attach(MIMEText(html_full, "html", "utf-8"))

    # Inline logo
    logo_cid = "bcc_logo_sig"
    if LOGO_PATH.is_file():
        with open(LOGO_PATH, "rb") as f:
            logo_data = f.read()
        logo_part = MIMEImage(logo_data, _subtype="png")
        logo_part.add_header("Content-ID", f"<{logo_cid}>")
        logo_part.add_header("Content-Disposition", "inline", filename="bcc_logo.png")
        outer.attach(logo_part)

    # Optional PDF attachment
    if attachment_path and os.path.isfile(attachment_path):
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        outer.attach(part)

    return outer


def _smtp_send(msg: MIMEMultipart, from_addr: str, recipients: list[str]) -> tuple[bool, str]:
    user     = os.environ.get("PRIV_MAIL1_USER", "").strip().strip('"')
    password = os.environ.get("PRIV_MAIL1_PASS", "").strip().strip('"')
    host     = os.environ.get("PRIV_MAIL1_SMTP", "smtp.privateemail.com").strip().strip('"')
    if not user or not password:
        return False, "Missing PRIV_MAIL1_USER / PRIV_MAIL1_PASS in .env"
    try:
        with smtplib.SMTP(host, 587) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, recipients, msg.as_string())
        return True, f"Sent from {from_addr} to {recipients[0]}, CC {', '.join(recipients[1:])}"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP auth failed: {e}"
    except Exception as e:
        return False, str(e)


# ── Public API ────────────────────────────────────────────────────────────────

def send_from_admin(
    to_email: str, subject: str, body_plain: str, cc: str | None = None
) -> tuple[bool, str]:
    """Send HTML email from admin@ with inline logo + signature. CC ycao@ automatically."""
    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (CC_YCAO, to_email):
                cc_list.append(e)

    msg = _build_html_message(ADMIN_FROM, to_email, subject, body_plain, cc_list)
    return _smtp_send(msg, ADMIN_FROM, [to_email] + cc_list)


def send_from_admin_with_attachment(
    to_email: str, subject: str, body_plain: str, attachment_path: str,
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from admin@ with PDF attachment + inline logo + signature."""
    if not os.path.isfile(attachment_path):
        return False, f"Attachment not found: {attachment_path}"

    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (CC_YCAO, to_email):
                cc_list.append(e)

    msg = _build_html_message(ADMIN_FROM, to_email, subject, body_plain, cc_list, attachment_path)
    return _smtp_send(msg, ADMIN_FROM, [to_email] + cc_list)
