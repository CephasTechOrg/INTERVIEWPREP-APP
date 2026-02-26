import logging
import smtplib
from email.mime.text import MIMEText

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Minimal email sender. For dev, it will print to console if SMTP is not configured.
    """
    sendgrid_key = getattr(settings, "SENDGRID_API_KEY", None)
    sendgrid_from = getattr(settings, "FROM_EMAIL", None) or getattr(settings, "SMTP_FROM", None)
    if sendgrid_key and sendgrid_from:
        try:
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": sendgrid_from},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            }
            headers = {
                "Authorization": f"Bearer {sendgrid_key}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=10) as client:
                resp = client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"SendGrid error {resp.status_code}: {resp.text}")
            logger.info("EMAIL: Successfully sent email to %s via SendGrid", to_email)
            return
        except Exception as e:
            logger.exception("EMAIL ERROR: SendGrid failed for %s: %s", to_email, str(e))
            raise  # Re-raise to allow caller to handle

    host = getattr(settings, "SMTP_HOST", None)
    port = getattr(settings, "SMTP_PORT", None)
    user = getattr(settings, "SMTP_USERNAME", None)
    pwd = getattr(settings, "SMTP_PASSWORD", None)
    sender = getattr(settings, "SMTP_FROM", None) or getattr(settings, "SMTP_USERNAME", None)

    if not host or not port or not sender:
        logger.info("[EMAIL DEV] To: %s Subject: %s Body: %s", to_email, subject, body)
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    try:
        with smtplib.SMTP(host, port) as server:
            if getattr(settings, "SMTP_TLS", False):
                server.starttls()
            if user and pwd:
                server.login(user, pwd)
            server.sendmail(sender, [to_email], msg.as_string())
    except Exception as e:
        logger.exception("EMAIL ERROR: Failed to send to %s: %s", to_email, str(e))
