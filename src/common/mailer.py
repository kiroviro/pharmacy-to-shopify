"""
Gmail SMTP mailer for DSA campaign alerts.

Credentials read from environment variables:
    GMAIL_ADDRESS     — sender address (e.g. kiril.kirov@gmail.com)
    GMAIL_APP_PASSWORD — Gmail app password (16-char, no spaces)

Usage:
    from src.common.mailer import send_alert
    send_alert(subject="...", body="...")
"""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def send_alert(subject: str, body: str, to: str | None = None) -> None:
    """Send a plain-text alert email via Gmail SMTP.

    Args:
        subject: Email subject line.
        body: Plain-text email body.
        to: Recipient address. Defaults to GMAIL_ADDRESS (self-send).

    Raises:
        RuntimeError: If GMAIL_ADDRESS or GMAIL_APP_PASSWORD are not set.
        smtplib.SMTPException: On SMTP errors.
    """
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not app_password:
        raise RuntimeError(
            "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in environment / .env"
        )

    recipient = to or gmail_address

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, app_password)
        smtp.sendmail(gmail_address, [recipient], msg.as_string())
