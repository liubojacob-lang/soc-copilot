"""Email notification provider."""

from __future__ import annotations

import asyncio
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .base import NotificationMessage, NotificationProvider


class EmailProvider(NotificationProvider):
    name = "email"

    def __init__(self):
        self.to_email = os.getenv("ALERT_EMAIL_TO")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    def is_configured(self) -> bool:
        return bool(self.to_email and self.smtp_user and self.smtp_password)

    async def send(self, message: NotificationMessage) -> bool:
        if not self.is_configured():
            return False
        return await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: NotificationMessage) -> bool:
        mail = MIMEMultipart("alternative")
        mail["Subject"] = message.title
        mail["From"] = self.smtp_user
        mail["To"] = self.to_email
        mail.attach(MIMEText(message.body, "plain", "utf-8"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, [self.to_email], mail.as_string())
        return True
