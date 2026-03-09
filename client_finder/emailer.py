"""
emailer.py – Send personalised pitch emails via SMTP.

Uses STARTTLS (port 587 by default) for secure delivery.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from client_finder import config

logger = logging.getLogger(__name__)


def send_pitch_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> bool:
    """
    Send a plain-text pitch email to *to_email*.

    Parameters
    ----------
    to_email : str
        Recipient email address.
    to_name : str
        Recipient display name (used in the To: header).
    subject : str
        Email subject line.
    body : str
        Plain-text email body.

    Returns
    -------
    bool
        True if the email was sent successfully, False otherwise.
    """
    if not to_email:
        logger.warning("No email address for '%s' – skipping.", to_name)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.EMAIL_FROM_NAME} <{config.SMTP_USER}>"
    msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, [to_email], msg.as_string())
        logger.info("Email sent to %s <%s>", to_name, to_email)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email to %s <%s>: %s", to_name, to_email, exc)
        return False
