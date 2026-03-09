"""
tests/test_scraper.py – Unit tests for client_finder.scraper utilities.

All external I/O (HTTP requests, SerpAPI calls) is mocked so tests run
without network access or real API keys.
"""

from __future__ import annotations

import types
import unittest
from unittest.mock import patch
import sys


def _import_scraper():
    """Import scraper without triggering config validation."""
    # Only stub the config sub-module; leave the real package in place
    config_stub = types.ModuleType("client_finder.config")
    config_stub.SERPAPI_API_KEY = "test_key"
    sys.modules["client_finder.config"] = config_stub

    if "client_finder.scraper" in sys.modules:
        return sys.modules["client_finder.scraper"]
    import client_finder.scraper as scraper_mod
    return scraper_mod


scraper = _import_scraper()


class TestEmailExtraction(unittest.TestCase):
    def test_extract_valid_email(self):
        text = "Contact us at hello@example.com for more info."
        emails = scraper._extract_emails(text)
        self.assertIn("hello@example.com", emails)

    def test_extract_multiple_emails(self):
        text = "Email a@b.com or c@d.org"
        emails = scraper._extract_emails(text)
        self.assertEqual(len(emails), 2)

    def test_no_emails(self):
        self.assertEqual(scraper._extract_emails("No emails here!"), [])

    def test_emails_are_lowercased(self):
        emails = scraper._extract_emails("Contact UPPER@Example.COM")
        self.assertIn("upper@example.com", emails)


class TestPhoneExtraction(unittest.TestCase):
    def test_extracts_phone(self):
        text = "Call us on +91 98765 43210"
        phones = scraper._extract_phones(text)
        self.assertTrue(len(phones) >= 1)

    def test_no_phones(self):
        result = scraper._extract_phones("No phone here.")
        self.assertEqual(result, [])


class TestMakeProspect(unittest.TestCase):
    def test_default_email_sent(self):
        p = scraper.make_prospect(name="Acme Corp")
        self.assertEqual(p["email_sent"], "No")

    def test_all_keys_present(self):
        p = scraper.make_prospect()
        expected_keys = {
            "name", "business_type", "website", "email",
            "phone", "linkedin_url", "location", "description",
            "source_url", "email_sent",
        }
        self.assertEqual(set(p.keys()), expected_keys)

    def test_name_stripped(self):
        p = scraper.make_prospect(name="  Acme  ")
        self.assertEqual(p["name"], "Acme")


class TestBuildQueries(unittest.TestCase):
    def test_returns_four_queries(self):
        queries = scraper._build_queries("restaurant", "Mumbai", ["no website"])
        self.assertEqual(len(queries), 4)

    def test_queries_contain_business_type(self):
        queries = scraper._build_queries("startup", "London", [])
        self.assertTrue(all("startup" in q for q in queries))

    def test_queries_contain_location(self):
        queries = scraper._build_queries("cafe", "Paris", [])
        self.assertTrue(all("Paris" in q for q in queries))


class TestParseLinkedInSnippet(unittest.TestCase):
    def test_extracts_name(self):
        result = {
            "title": "Jane Doe – Marketing Manager | LinkedIn",
            "snippet": "Experienced marketer in Mumbai.",
            "link": "https://www.linkedin.com/in/jane-doe",
        }
        p = scraper._parse_linkedin_snippet(result, "marketing", "Mumbai")
        self.assertEqual(p["name"], "Jane Doe")

    def test_sets_linkedin_url(self):
        result = {
            "title": "Test Company | LinkedIn",
            "snippet": "",
            "link": "https://www.linkedin.com/company/test-company",
        }
        p = scraper._parse_linkedin_snippet(result, "tech", "NYC")
        self.assertEqual(p["linkedin_url"], "https://www.linkedin.com/company/test-company")


class TestParseWebResult(unittest.TestCase):
    def test_extracts_email_from_snippet(self):
        result = {
            "title": "Acme Design | Home",
            "snippet": "Reach us at design@acme.io for quotes.",
            "link": "https://acme.io",
        }
        p = scraper._parse_web_result(result, "design", "NYC")
        self.assertEqual(p["email"], "design@acme.io")

    def test_sets_website(self):
        result = {
            "title": "Test Biz",
            "snippet": "",
            "link": "https://testbiz.com",
        }
        p = scraper._parse_web_result(result, "retail", "LA")
        self.assertEqual(p["website"], "https://testbiz.com")


class TestFindProspectsMocked(unittest.TestCase):
    @patch("client_finder.scraper._enrich_from_page", side_effect=lambda p: p)
    @patch("client_finder.scraper._serpapi_search")
    @patch("client_finder.scraper.time.sleep")
    def test_returns_prospects(self, mock_sleep, mock_search, mock_enrich):
        mock_search.return_value = [
            {
                "title": "Cool Cafe | LinkedIn",
                "snippet": "A trendy cafe in Mumbai.",
                "link": "https://www.linkedin.com/company/cool-cafe",
            },
            {
                "title": "Brew Masters",
                "snippet": "Contact: brew@masters.com",
                "link": "https://brewmasters.com",
            },
        ]
        results = scraper.find_prospects("cafe", "Mumbai", ["trendy"], max_results=5)
        self.assertTrue(len(results) >= 1)

    @patch("client_finder.scraper._enrich_from_page", side_effect=lambda p: p)
    @patch("client_finder.scraper._serpapi_search", return_value=[])
    @patch("client_finder.scraper.time.sleep")
    def test_empty_search_returns_empty_list(self, mock_sleep, mock_search, mock_enrich):
        results = scraper.find_prospects("xyz", "nowhere", [], max_results=10)
        self.assertEqual(results, [])

    @patch("client_finder.scraper._enrich_from_page", side_effect=lambda p: p)
    @patch("client_finder.scraper._serpapi_search")
    @patch("client_finder.scraper.time.sleep")
    def test_deduplication(self, mock_sleep, mock_search, mock_enrich):
        """The same URL should not appear twice."""
        duplicate_result = {
            "title": "Dup Cafe",
            "snippet": "",
            "link": "https://dupcafe.com",
        }
        mock_search.return_value = [duplicate_result, duplicate_result]
        results = scraper.find_prospects("cafe", "Mumbai", [], max_results=10)
        urls = [r["source_url"] for r in results]
        self.assertEqual(len(urls), len(set(urls)))


if __name__ == "__main__":
    unittest.main()
