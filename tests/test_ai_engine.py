"""
tests/test_ai_engine.py – Unit tests for client_finder.ai_engine.

OpenAI API calls are mocked so no real API key is needed.
"""

from __future__ import annotations

import types
import unittest
from unittest.mock import MagicMock, patch
import sys


def _setup_stubs():
    config_stub = types.ModuleType("client_finder.config")
    config_stub.OPENAI_API_KEY = "sk-test"
    config_stub.STUDIO_NAME = "Test Studio"
    config_stub.STUDIO_WEBSITE = "https://teststudio.com"
    config_stub.STUDIO_PORTFOLIO = "https://teststudio.com/portfolio"
    sys.modules["client_finder.config"] = config_stub


_setup_stubs()
import client_finder.ai_engine as ai_engine_mod


class TestBuildUserPrompt(unittest.TestCase):
    def test_contains_prospect_name(self):
        p = {
            "name": "Acme Corp",
            "business_type": "startup",
            "description": "A cool startup",
            "location": "NYC",
            "website": "https://acme.com",
        }
        prompt = ai_engine_mod._build_user_prompt(p)
        self.assertIn("Acme Corp", prompt)

    def test_contains_studio_name(self):
        p = {"name": "Test", "business_type": "cafe"}
        prompt = ai_engine_mod._build_user_prompt(p)
        self.assertIn("Test Studio", prompt)

    def test_subject_format_instruction(self):
        p = {}
        prompt = ai_engine_mod._build_user_prompt(p)
        self.assertIn("SUBJECT:", prompt)


class TestParseResponse(unittest.TestCase):
    def test_parses_subject_and_body(self):
        raw = "SUBJECT: Hello World\n\nDear Jane,\n\nWe'd love to work with you."
        prospect = {"name": "Jane"}
        subject, body = ai_engine_mod._parse_response(raw, prospect)
        self.assertEqual(subject, "Hello World")
        self.assertIn("Dear Jane", body)

    def test_fallback_subject_when_missing(self):
        raw = "Dear friend, please check us out."
        prospect = {"name": "Bob"}
        subject, body = ai_engine_mod._parse_response(raw, prospect)
        self.assertIn("Bob", subject)

    def test_body_not_empty_for_valid_response(self):
        raw = "SUBJECT: Great opportunity\n\nHi there, we have great news!"
        subject, body = ai_engine_mod._parse_response(raw, {})
        self.assertTrue(len(body) > 0)


class TestGeneratePitchEmailMocked(unittest.TestCase):
    @patch("client_finder.ai_engine._get_client")
    def test_returns_subject_and_body(self, mock_get_client):
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "SUBJECT: Elevate Your Brand\n\nDear Acme,\n\nWe'd love to help."
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )
        mock_get_client.return_value = mock_client

        prospect = {"name": "Acme", "business_type": "startup", "email": "hi@acme.com"}
        subject, body = ai_engine_mod.generate_pitch_email(prospect)

        self.assertEqual(subject, "Elevate Your Brand")
        self.assertIn("Acme", body)


if __name__ == "__main__":
    unittest.main()
