"""
tests/test_emailer.py – Unit tests for client_finder.emailer.

SMTP connections are fully mocked.
"""

from __future__ import annotations

import types
import unittest
from unittest.mock import MagicMock, patch
import sys


def _setup_stubs():
    config_stub = types.ModuleType("client_finder.config")
    config_stub.SMTP_HOST = "smtp.example.com"
    config_stub.SMTP_PORT = 587
    config_stub.SMTP_USER = "sender@example.com"
    config_stub.SMTP_PASSWORD = "password"
    config_stub.EMAIL_FROM_NAME = "Test Studio"
    sys.modules["client_finder.config"] = config_stub


_setup_stubs()
import client_finder.emailer as emailer_mod


class TestSendPitchEmail(unittest.TestCase):
    @patch("client_finder.emailer.smtplib.SMTP")
    def test_returns_true_on_success(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = emailer_mod.send_pitch_email(
            to_email="client@example.com",
            to_name="Client Name",
            subject="Hello",
            body="This is a test email.",
        )
        self.assertTrue(result)

    def test_returns_false_for_empty_email(self):
        result = emailer_mod.send_pitch_email(
            to_email="",
            to_name="Nobody",
            subject="Hi",
            body="Body",
        )
        self.assertFalse(result)

    @patch("client_finder.emailer.smtplib.SMTP")
    def test_returns_false_on_smtp_error(self, mock_smtp_cls):
        import smtplib
        mock_smtp_cls.return_value.__enter__ = MagicMock(
            side_effect=smtplib.SMTPException("Connection refused")
        )
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = emailer_mod.send_pitch_email(
            to_email="client@example.com",
            to_name="Client",
            subject="Hi",
            body="Body",
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
