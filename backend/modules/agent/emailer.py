import email
import os
import smtplib
import ssl
import time
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
OUTBOX_DIR = DATA_DIR / "outbox"

_last_test_email_time = 0.0


def _clean_header(val: str, max_len: int = 150) -> str:
    s = "".join(ch for ch in str(val or "") if ch not in "\r\n")
    return s[:max_len].strip()


def build_mime_message(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str,
    attachment_csv: Optional[str] = None,
    attachment_filename: str = "flagged_transactions.csv",
) -> MIMEMultipart:
    clean_to = _clean_header(to_email)
    clean_from = _clean_header(from_email)
    clean_subject = _clean_header(subject)

    # Root container
    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(clean_subject, "utf-8")
    msg["From"] = clean_from
    msg["To"] = clean_to
    msg["Date"] = email.utils.formatdate(localtime=True)

    # Alternative container for text and html
    msg_alt = MIMEMultipart("alternative")
    part_text = MIMEText(text_body or "", "plain", "utf-8")
    part_html = MIMEText(html_body or "", "html", "utf-8")
    msg_alt.attach(part_text)
    msg_alt.attach(part_html)
    msg.attach(msg_alt)

    # Optional CSV attachment
    if attachment_csv is not None:
        csv_bytes = attachment_csv.encode("utf-8")
        part_csv = MIMEApplication(csv_bytes, Name=_clean_header(attachment_filename, 50))
        part_csv.add_header(
            "Content-Disposition",
            "attachment",
            filename=_clean_header(attachment_filename, 50),
        )
        msg.attach(part_csv)

    return msg


def send_email(
    to_email: str,
    subject: str,
    html_body: str = "",
    text_body: str = "",
    attachment_csv: Optional[str] = None,
    attachment_filename: str = "flagged_transactions.csv",
    html_content: Optional[str] = None,
    text_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Dispatches email according to EMAIL_MODE (dry_run or smtp).
    
    Dry run: saves .eml to backend/data/outbox/ and returns success.
    SMTP: connects with STARTTLS (587) or SSL (465) and transmits message.
    """
    if html_content is not None and not html_body:
        html_body = html_content
    if text_content is not None and not text_body:
        text_body = text_content
    to_email = _clean_header(to_email)
    if not to_email or "@" not in to_email:
        raise ValueError("Recipient owner email is missing or invalid.")

    email_mode = os.getenv("EMAIL_MODE", "dry_run").strip().lower()
    from_email = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "finpilot@aaravretail.com"

    msg = build_mime_message(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        from_email=from_email,
        attachment_csv=attachment_csv,
        attachment_filename=attachment_filename,
    )

    if email_mode != "smtp":
        # DRY RUN: Save .eml to backend/data/outbox/
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        eml_filename = f"email_{ts}_{_clean_header(to_email, 20)}.eml"
        eml_path = OUTBOX_DIR / eml_filename
        with open(eml_path, "wb") as f:
            f.write(msg.as_bytes())

        return {
            "success": True,
            "mode": "dry_run",
            "sent_to": to_email,
            "eml_file": str(eml_path),
            "message": f"Dry run: report saved to outbox/{eml_filename}, not emailed.",
        }

    # LIVE SMTP
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        port = 587
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()

    if not host or not user or not password:
        raise RuntimeError("SMTP configuration incomplete. Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in backend/.env.")

    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20.0) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20.0) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)

        return {
            "success": True,
            "mode": "smtp",
            "sent_to": to_email,
            "message": f"Report emailed to {to_email}.",
        }

    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError(
            "The mail server rejected the login. For Gmail use an App Password, not your normal password."
        ) from e
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
        raise RuntimeError(
            "Could not reach the mail server. A firewall or college network may be blocking it."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Email delivery failed: {e}") from e


def send_test_email(to_email: str) -> Dict[str, Any]:
    """Sends a one-line test message rate-limited to once per 30 seconds."""
    global _last_test_email_time
    now = time.time()
    elapsed = now - _last_test_email_time
    if elapsed < 30.0:
        remaining = int(30.0 - elapsed)
        raise RuntimeError(f"Please wait {remaining} seconds before sending another test email.")

    subject = "[FinPilot] Test Email Verification"
    body_text = (
        "This is a test notification from FinPilot AI confirming your email settings.\n\n"
        "Your automated financial analyst agent is configured and active.\n"
    )
    body_html = (
        "<!DOCTYPE html><html><body style='font-family: Arial, sans-serif; background-color: #F3F5F8; padding: 24px;'>"
        "<div style='max-width: 480px; margin: 0 auto; background: #FFFFFF; padding: 24px; border-radius: 8px; border: 1px solid #E3E7EE;'>"
        "<h3 style='margin: 0 0 10px; color: #10141B;'>FinPilot AI &mdash; Test Email</h3>"
        "<p style='font-size: 13.5px; color: #5B6475; line-height: 1.5; margin: 0 0 16px;'>"
        "This is a test notification from FinPilot AI confirming your email settings."
        "</p>"
        "<p style='font-size: 12px; color: #8A93A6; margin: 0;'>"
        "Your automated financial analyst agent is configured and active."
        "</p>"
        "</div></body></html>"
    )

    result = send_email(
        to_email=to_email,
        subject=subject,
        html_body=body_html,
        text_body=body_text,
    )
    _last_test_email_time = time.time()
    return result
