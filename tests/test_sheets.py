"""
tests/test_sheets.py – Unit tests for client_finder.sheets helpers.

The Google Sheets API is fully mocked; no credentials required.
"""

from __future__ import annotations

import types
import unittest
from unittest.mock import MagicMock, patch
import sys


def _setup_stubs():
    """Inject minimal stubs so sheets.py can be imported without credentials."""
    config_stub = types.ModuleType("client_finder.config")
    config_stub.GOOGLE_SERVICE_ACCOUNT_JSON = "fake/path.json"
    config_stub.GOOGLE_SHEET_ID = "fake_sheet_id"
    sys.modules["client_finder.config"] = config_stub


_setup_stubs()
import client_finder.sheets as sheets_mod


class TestProspectToRow(unittest.TestCase):
    def test_correct_ordering(self):
        p = {
            "name": "Test Co",
            "business_type": "startup",
            "website": "https://test.co",
            "email": "hi@test.co",
            "phone": "123",
            "linkedin_url": "https://linkedin.com/company/test",
            "location": "NYC",
            "description": "A test company",
            "source_url": "https://test.co",
            "email_sent": "No",
        }
        row = sheets_mod._prospect_to_row(p)
        self.assertEqual(row[0], "Test Co")           # Name
        self.assertEqual(row[3], "hi@test.co")        # Email
        self.assertEqual(row[9], "No")                # Email Sent

    def test_missing_keys_default_empty(self):
        row = sheets_mod._prospect_to_row({})
        self.assertEqual(len(row), len(sheets_mod.HEADERS))
        self.assertTrue(all(v == "" for v in row))


class TestColLetter(unittest.TestCase):
    def test_first_column(self):
        self.assertEqual(sheets_mod._col_letter(0), "A")

    def test_tenth_column(self):
        self.assertEqual(sheets_mod._col_letter(9), "J")


class TestHeaders(unittest.TestCase):
    def test_email_sent_last(self):
        self.assertEqual(sheets_mod.HEADERS[-1], "Email Sent")

    def test_ten_headers(self):
        self.assertEqual(len(sheets_mod.HEADERS), 10)


if __name__ == "__main__":
    unittest.main()
