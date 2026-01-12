import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Minimal email sender. For dev, it will print to console if SMTP is not configured.
    """
    host = getattr(settings, "SMTP_HOST", None)
    port = getattr(settings, "SMTP_PORT", None)
    user = getattr(settings, "SMTP_USERNAME", None)
    pwd = getattr(settings, "SMTP_PASSWORD", None)
    sender = getattr(settings, "SMTP_FROM", None) or getattr(settings, "SMTP_USERNAME", None)

    if not host or not port or not sender:
        print(f"[EMAIL DEV] To: {to_email}\nSubject: {subject}\n\n{body}")
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
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
