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
YCAO_FROM  = "ycao@buildingcodeconsulting.com"
CC_YCAO    = "ycao@buildingcodeconsulting.com"
KCY_FROM   = "ycao@kcyengineer.com"

# ── Brands ────────────────────────────────────────────────────────────────────
# Each brand carries its own signature block + inline logo.
# Keep BCC_BRAND addresses untouched — BCC senders use this by default.
# KCY_BRAND is an entirely separate identity for ycao@kcyengineer.com outreach.

BCC_BRAND = {
    "name":       "Kevin C., PE, MCP",
    "title":      "Professional In Charge/President",
    "company":    "Building Code Consulting LLC",
    "cell":       "(571) 365-6937",
    "logo_path":  Path(__file__).resolve().parent.parent / "Marketing" / "Business Card BCC Kevin C..png",
    "logo_cid":   "bcc_logo_sig",
    "logo_alt":   "BCC Logo",
    "logo_width": 240,
}

KCY_BRAND = {
    "name":       "Kyle Cao",
    "title":      "Professional In Charge",
    "company":    "KCY Engineer PLLC",
    "cell":       "(571) 365-6937",
    "logo_path":  Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Logo E-Sig Stamp\KCY LOGO.png"),
    "logo_cid":   "kcy_logo_sig",
    "logo_alt":   "KCY Engineer Logo",
    "logo_width": 240,
}

# Backwards-compat alias (unused now but kept in case external scripts import it)
LOGO_PATH = BCC_BRAND["logo_path"]


def _sig_email(from_addr: str, brand: dict) -> str:
    """Return the email shown in the signature — always the actual sending address,
    except for Gmail sends which show admin@ (established convention)."""
    addr = from_addr.lower().strip()
    if brand is KCY_BRAND:
        return KCY_FROM
    if "ycao@building" in addr:
        return CC_YCAO
    if "gmail" in addr:
        return ADMIN_FROM
    return ADMIN_FROM


def _signature_plain(from_addr: str, brand: dict = BCC_BRAND) -> str:
    return (
        f"\n\n--\n"
        f"{brand['name']}\n"
        f"{brand['title']}\n"
        f"{brand['company']}\n"
        f"Cell: {brand['cell']}\n"
        f"{_sig_email(from_addr, brand)}"
    )


def _signature_html(from_addr: str, brand: dict = BCC_BRAND) -> str:
    email_line = _sig_email(from_addr, brand)
    logo_cid = brand["logo_cid"]
    logo_alt = brand["logo_alt"]
    logo_w   = brand["logo_width"]
    return f"""
<table cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;">
  <tr>
    <td style="font-family:Arial,sans-serif;font-size:10pt;color:#222;line-height:1.6;">
      <strong>{brand['name']}</strong><br>
      {brand['title']}<br>
      {brand['company']}<br>
      Cell: {brand['cell']}<br>
      <a href="mailto:{email_line}" style="color:#1a73e8;text-decoration:none;">{email_line}</a>
    </td>
  </tr>
  <tr>
    <td style="padding-top:8px;">
      <img src="cid:{logo_cid}" alt="{logo_alt}" width="{logo_w}" style="width:{logo_w}px;max-width:{logo_w}px;height:auto;">
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
    attachment_paths: list[str] | None = None,
    brand: dict = BCC_BRAND,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> MIMEMultipart:
    """
    Build a multipart/related HTML email with:
      - Plain text fallback
      - HTML body with brand-specific signature block
      - Inline brand logo (cid per brand)
      - Optional PDF attachment
      - Optional threading headers (In-Reply-To, References) for proper reply chain
    """
    # Outer container: related (holds html + inline image)
    outer = MIMEMultipart("related")
    outer["From"]    = from_addr
    outer["To"]      = to_email
    outer["Subject"] = subject
    if cc_list:
        outer["Cc"]  = ", ".join(cc_list)
    if in_reply_to:
        outer["In-Reply-To"] = in_reply_to
    if references:
        outer["References"] = references
    elif in_reply_to:
        outer["References"] = in_reply_to

    # Alternative: plain + html
    alt = MIMEMultipart("alternative")
    outer.attach(alt)

    # Plain text version (body + text signature)
    plain_full = body_plain + _signature_plain(from_addr, brand)
    alt.attach(MIMEText(plain_full, "plain", "utf-8"))

    # HTML version
    _style = "font-family:Arial,sans-serif;font-size:11pt;color:#222;line-height:1.7;"
    body_html = body_plain.replace("\n\n", f'</p><p style="{_style}">').replace("\n", "<br>")
    html_full = f"""<html><body>
<div style="max-width:620px;">
<p style="{_style}">
{body_html}
</p>
</div>
{_signature_html(from_addr, brand)}
</body></html>"""
    alt.attach(MIMEText(html_full, "html", "utf-8"))

    # Inline logo (brand-specific)
    logo_path = brand["logo_path"]
    logo_cid  = brand["logo_cid"]
    if logo_path.is_file():
        with open(logo_path, "rb") as f:
            logo_data = f.read()
        logo_part = MIMEImage(logo_data, _subtype="png")
        logo_part.add_header("Content-ID", f"<{logo_cid}>")
        logo_part.add_header("Content-Disposition", "inline", filename=logo_path.name)
        outer.attach(logo_part)

    # Attachments (single or multiple)
    all_attachments = list(attachment_paths or [])
    if attachment_path and attachment_path not in all_attachments:
        all_attachments.append(attachment_path)
    for apath in all_attachments:
        if os.path.isfile(apath):
            filename = os.path.basename(apath)
            with open(apath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            outer.attach(part)

    return outer


def _smtp_send(
    msg: MIMEMultipart,
    from_addr: str,
    recipients: list[str],
    user_env: str = "PRIV_MAIL1_USER",
    pass_env: str = "PRIV_MAIL1_PASS",
    host_env: str = "PRIV_MAIL1_SMTP",
    host_default: str = "smtp.privateemail.com",
) -> tuple[bool, str]:
    user     = os.environ.get(user_env, "").strip().strip('"')
    password = os.environ.get(pass_env, "").strip().strip('"')
    host     = os.environ.get(host_env, host_default).strip().strip('"')
    if not user or not password:
        return False, f"Missing {user_env} / {pass_env} in .env"
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
    to_email: str, subject: str, body_plain: str, cc: str | None = None,
    in_reply_to: str | None = None, references: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from admin@ with inline logo + signature. CC ycao@ automatically.
    Pass in_reply_to / references to thread the message under an existing conversation."""
    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (CC_YCAO, to_email):
                cc_list.append(e)

    msg = _build_html_message(ADMIN_FROM, to_email, subject, body_plain, cc_list,
                              in_reply_to=in_reply_to, references=references)
    return _smtp_send(msg, ADMIN_FROM, [to_email] + cc_list)


def send_from_admin_with_attachment(
    to_email: str, subject: str, body_plain: str, attachment_path: str,
    cc: str | None = None,
    in_reply_to: str | None = None, references: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from admin@ with PDF attachment + inline logo + signature.
    Pass in_reply_to / references to thread the message under an existing conversation."""
    if not os.path.isfile(attachment_path):
        return False, f"Attachment not found: {attachment_path}"

    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (CC_YCAO, to_email):
                cc_list.append(e)

    msg = _build_html_message(ADMIN_FROM, to_email, subject, body_plain, cc_list, attachment_path,
                              in_reply_to=in_reply_to, references=references)
    return _smtp_send(msg, ADMIN_FROM, [to_email] + cc_list)


def send_from_ycao(
    to_email: str, subject: str, body_plain: str, cc: str | None = None
) -> tuple[bool, str]:
    """Send HTML email from ycao@ (uses PRIV_MAIL2_* SMTP). CC admin@ automatically."""
    cc_list = [ADMIN_FROM]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (ADMIN_FROM, to_email):
                cc_list.append(e)

    msg = _build_html_message(YCAO_FROM, to_email, subject, body_plain, cc_list)
    return _smtp_send(
        msg, YCAO_FROM, [to_email] + cc_list,
        user_env="PRIV_MAIL2_USER", pass_env="PRIV_MAIL2_PASS",
        host_env="PRIV_MAIL2_SMTP",
    )


def send_from_ycao_with_attachment(
    to_email: str, subject: str, body_plain: str, attachment_path: str,
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from ycao@ with PDF attachment. CC admin@ automatically."""
    if not os.path.isfile(attachment_path):
        return False, f"Attachment not found: {attachment_path}"

    cc_list = [ADMIN_FROM]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (ADMIN_FROM, to_email):
                cc_list.append(e)

    msg = _build_html_message(YCAO_FROM, to_email, subject, body_plain, cc_list, attachment_path)
    return _smtp_send(
        msg, YCAO_FROM, [to_email] + cc_list,
        user_env="PRIV_MAIL2_USER", pass_env="PRIV_MAIL2_PASS",
        host_env="PRIV_MAIL2_SMTP",
    )


def send_from_admin_with_attachments(
    to_email: str, subject: str, body_plain: str, attachment_paths: list[str],
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from admin@ with multiple PDF attachments. CC ycao@."""
    for p in attachment_paths:
        if not os.path.isfile(p):
            return False, f"Attachment not found: {p}"

    cc_list = [CC_YCAO]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (CC_YCAO, to_email):
                cc_list.append(e)

    msg = _build_html_message(ADMIN_FROM, to_email, subject, body_plain, cc_list,
                              attachment_paths=attachment_paths)
    return _smtp_send(msg, ADMIN_FROM, [to_email] + cc_list)


def send_from_ycao_with_attachments(
    to_email: str, subject: str, body_plain: str, attachment_paths: list[str],
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from ycao@ with multiple PDF attachments. CC admin@."""
    for p in attachment_paths:
        if not os.path.isfile(p):
            return False, f"Attachment not found: {p}"

    cc_list = [ADMIN_FROM]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (ADMIN_FROM, to_email):
                cc_list.append(e)

    msg = _build_html_message(YCAO_FROM, to_email, subject, body_plain, cc_list,
                              attachment_paths=attachment_paths)
    return _smtp_send(
        msg, YCAO_FROM, [to_email] + cc_list,
        user_env="PRIV_MAIL2_USER", pass_env="PRIV_MAIL2_PASS",
        host_env="PRIV_MAIL2_SMTP",
    )


# ── KCY Engineer senders (ycao@kcyengineer.com, PRIV_MAIL3_*) ────────────────
# KCY is a SEPARATE BRAND. No BCC addresses appear anywhere (no CC, no sig crossover).
# Default CC is empty so recipients never see a buildingcodeconsulting.com address.

def send_from_kcy(
    to_email: str, subject: str, body_plain: str, cc: str | None = None
) -> tuple[bool, str]:
    """Send HTML email from ycao@kcyengineer.com with KCY signature + logo. No CC by default."""
    cc_list: list[str] = []
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e != to_email:
                cc_list.append(e)

    msg = _build_html_message(KCY_FROM, to_email, subject, body_plain, cc_list, brand=KCY_BRAND)
    return _smtp_send(
        msg, KCY_FROM, [to_email] + cc_list,
        user_env="PRIV_MAIL3_USER", pass_env="PRIV_MAIL3_PASS",
        host_env="PRIV_MAIL3_SMTP",
    )


def send_from_kcy_with_attachment(
    to_email: str, subject: str, body_plain: str, attachment_path: str,
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from ycao@kcyengineer.com with PDF attachment + KCY sig. No CC by default."""
    if not os.path.isfile(attachment_path):
        return False, f"Attachment not found: {attachment_path}"

    cc_list: list[str] = []
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e != to_email:
                cc_list.append(e)

    msg = _build_html_message(KCY_FROM, to_email, subject, body_plain, cc_list,
                              attachment_path, brand=KCY_BRAND)
    return _smtp_send(
        msg, KCY_FROM, [to_email] + cc_list,
        user_env="PRIV_MAIL3_USER", pass_env="PRIV_MAIL3_PASS",
        host_env="PRIV_MAIL3_SMTP",
    )


def send_from_kcy_with_attachments(
    to_email: str, subject: str, body_plain: str, attachment_paths: list[str],
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from ycao@kcyengineer.com with multiple PDF attachments + KCY sig."""
    for p in attachment_paths:
        if not os.path.isfile(p):
            return False, f"Attachment not found: {p}"

    cc_list: list[str] = []
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e != to_email:
                cc_list.append(e)

    msg = _build_html_message(KCY_FROM, to_email, subject, body_plain, cc_list,
                              attachment_paths=attachment_paths, brand=KCY_BRAND)
    return _smtp_send(
        msg, KCY_FROM, [to_email] + cc_list,
        user_env="PRIV_MAIL3_USER", pass_env="PRIV_MAIL3_PASS",
        host_env="PRIV_MAIL3_SMTP",
    )


# ── Gmail senders ─────────────────────────────────────────────────────────────
GMAIL_FROM = os.environ.get("GMAIL_USER", "caoyueno5@gmail.com").strip().strip('"')


def send_from_gmail(
    to_email: str, subject: str, body_plain: str, cc: str | None = None
) -> tuple[bool, str]:
    """Send HTML email from Gmail (caoyueno5@gmail.com). CC admin@ automatically."""
    cc_list = [ADMIN_FROM]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (ADMIN_FROM, to_email):
                cc_list.append(e)

    msg = _build_html_message(GMAIL_FROM, to_email, subject, body_plain, cc_list)
    return _smtp_send(
        msg, GMAIL_FROM, [to_email] + cc_list,
        user_env="GMAIL_USER", pass_env="GMAIL_APP_PASS",
        host_env="GMAIL_SMTP", host_default="smtp.gmail.com",
    )


def send_from_gmail_with_attachment(
    to_email: str, subject: str, body_plain: str, attachment_path: str,
    cc: str | None = None,
) -> tuple[bool, str]:
    """Send HTML email from Gmail with PDF attachment. CC admin@ automatically."""
    if not os.path.isfile(attachment_path):
        return False, f"Attachment not found: {attachment_path}"

    cc_list = [ADMIN_FROM]
    if cc:
        for e in cc.replace(",", " ").split():
            e = e.strip()
            if e and e not in (ADMIN_FROM, to_email):
                cc_list.append(e)

    msg = _build_html_message(GMAIL_FROM, to_email, subject, body_plain, cc_list, attachment_path)
    return _smtp_send(
        msg, GMAIL_FROM, [to_email] + cc_list,
        user_env="GMAIL_USER", pass_env="GMAIL_APP_PASS",
        host_env="GMAIL_SMTP", host_default="smtp.gmail.com",
    )
