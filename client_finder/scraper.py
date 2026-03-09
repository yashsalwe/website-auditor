"""
scraper.py – Find potential design-studio clients via Google Search (SerpAPI).

Strategy
--------
1. Build targeted search queries that surface LinkedIn company/person profiles
   AND general web pages for businesses matching the user's criteria.
2. Parse each result page with BeautifulSoup to extract as much structured
   data as possible (name, business type, email, phone, website URL).
3. Return a de-duplicated list of :class:`Prospect` dicts.

Note on LinkedIn
----------------
Direct LinkedIn scraping violates their Terms of Service.  Instead we use
SerpAPI's Google-search endpoint with ``site:linkedin.com/in`` and
``site:linkedin.com/company`` queries, which surfaces publicly indexed
profile snippets without touching LinkedIn's servers directly.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from client_finder import config

logger = logging.getLogger(__name__)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

# Seconds to wait between HTTP requests so we stay polite
REQUEST_DELAY = 1.5


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

def make_prospect(
    *,
    name: str = "",
    business_type: str = "",
    website: str = "",
    email: str = "",
    phone: str = "",
    linkedin_url: str = "",
    source_url: str = "",
    description: str = "",
    location: str = "",
) -> dict[str, str]:
    """Return a standardised prospect dict."""
    return {
        "name": name.strip(),
        "business_type": business_type.strip(),
        "website": website.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "linkedin_url": linkedin_url.strip(),
        "location": location.strip(),
        "description": description.strip(),
        "source_url": source_url.strip(),
        "email_sent": "No",
    }


# ---------------------------------------------------------------------------
# SerpAPI helpers
# ---------------------------------------------------------------------------

def _serpapi_search(query: str, num: int = 10) -> list[dict[str, Any]]:
    """Run a Google search via SerpAPI and return organic results."""
    params = {
        "engine": "google",
        "q": query,
        "num": num,
        "api_key": config.SERPAPI_API_KEY,
    }
    try:
        resp = requests.get(SERPAPI_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("organic_results", [])
    except requests.RequestException as exc:
        logger.warning("SerpAPI request failed for query '%s': %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Email / phone extraction helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(\+?\d[\d\s\-().]{7,}\d)"
)


def _is_linkedin_url(url: str) -> bool:
    """Return True only when the URL's hostname is genuinely linkedin.com."""
    netloc = urlparse(url).netloc.lower()
    # Accepted: linkedin.com, www.linkedin.com, *.linkedin.com
    return netloc == "linkedin.com" or netloc.endswith(".linkedin.com")


def _extract_emails(text: str) -> list[str]:
    return list({m.lower() for m in _EMAIL_RE.findall(text)})


def _extract_phones(text: str) -> list[str]:
    raw = _PHONE_RE.findall(text)
    cleaned = []
    for p in raw:
        p = re.sub(r"\s+", " ", p).strip()
        if len(re.sub(r"\D", "", p)) >= 7:
            cleaned.append(p)
    return list(set(cleaned))


# ---------------------------------------------------------------------------
# Page scraping
# ---------------------------------------------------------------------------

def _fetch_page_text(url: str) -> str:
    """Download *url* and return visible text (best-effort)."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; ClientFinderBot/1.0; "
                "+https://github.com/yashsalwe/website-auditor)"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as exc:
        logger.debug("Could not fetch %s: %s", url, exc)
        return ""


def _enrich_from_page(prospect: dict[str, str]) -> dict[str, str]:
    """Visit the prospect's website and fill in missing email / phone."""
    url = prospect.get("website") or prospect.get("linkedin_url") or prospect.get("source_url")
    if not url:
        return prospect

    # Skip direct LinkedIn URLs – scraping them is against ToS
    if _is_linkedin_url(url):
        return prospect

    time.sleep(REQUEST_DELAY)
    text = _fetch_page_text(url)
    if not text:
        return prospect

    if not prospect["email"]:
        emails = _extract_emails(text)
        prospect["email"] = emails[0] if emails else ""

    if not prospect["phone"]:
        phones = _extract_phones(text)
        prospect["phone"] = phones[0] if phones else ""

    if not prospect["description"]:
        prospect["description"] = text[:300]

    return prospect


# ---------------------------------------------------------------------------
# Core search logic
# ---------------------------------------------------------------------------

def _build_queries(business_type: str, location: str, keywords: list[str]) -> list[str]:
    """Return a list of search queries for finding prospects."""
    kw_str = " ".join(keywords)
    queries = [
        # LinkedIn company profiles
        f'site:linkedin.com/company "{business_type}" "{location}" {kw_str}',
        # LinkedIn people profiles
        f'site:linkedin.com/in "{business_type}" "{location}" {kw_str}',
        # General web (contact pages, directories)
        f'"{business_type}" "{location}" {kw_str} contact email',
        # Business directories
        f'"{business_type}" "{location}" {kw_str} site:clutch.co OR site:yelp.com OR site:bark.com',
    ]
    return queries


def _parse_linkedin_snippet(result: dict[str, Any], business_type: str, location: str) -> dict[str, str]:
    """Extract prospect data from a SerpAPI LinkedIn organic result."""
    title = result.get("title", "")
    snippet = result.get("snippet", "")
    link = result.get("link", "")

    # Title format: "Person Name – Job Title | LinkedIn" or "Company | LinkedIn"
    name = title.split("|")[0].split("–")[0].split("-")[0].strip()
    description = snippet

    linkedin_url = link if _is_linkedin_url(link) else ""
    is_company = _is_linkedin_url(link) and "/company/" in urlparse(link).path

    return make_prospect(
        name=name,
        business_type=business_type,
        linkedin_url=linkedin_url,
        source_url=link,
        description=description,
        location=location,
    )


def _parse_web_result(result: dict[str, Any], business_type: str, location: str) -> dict[str, str]:
    """Extract prospect data from a general web organic result."""
    title = result.get("title", "")
    snippet = result.get("snippet", "")
    link = result.get("link", "")

    emails = _extract_emails(snippet)
    phones = _extract_phones(snippet)

    return make_prospect(
        name=title.split("|")[0].split("-")[0].strip(),
        business_type=business_type,
        website=link,
        email=emails[0] if emails else "",
        phone=phones[0] if phones else "",
        source_url=link,
        description=snippet,
        location=location,
    )


def find_prospects(
    business_type: str,
    location: str,
    keywords: list[str],
    max_results: int = 20,
) -> list[dict[str, str]]:
    """
    Search for potential clients matching the given criteria.

    Parameters
    ----------
    business_type:
        The industry/type of business to target (e.g. "restaurant", "startup").
    location:
        Geographic location to narrow the search (e.g. "Mumbai", "New York").
    keywords:
        Extra keywords to refine the search (e.g. ["no website", "new brand"]).
    max_results:
        Maximum number of unique prospects to return.

    Returns
    -------
    list of prospect dicts (see :func:`make_prospect` for keys).
    """
    queries = _build_queries(business_type, location, keywords)
    seen_urls: set[str] = set()
    prospects: list[dict[str, str]] = []

    for query in queries:
        if len(prospects) >= max_results:
            break

        logger.info("Searching: %s", query)
        results = _serpapi_search(query, num=10)
        time.sleep(REQUEST_DELAY)

        for result in results:
            if len(prospects) >= max_results:
                break

            link = result.get("link", "")
            if link in seen_urls:
                continue
            seen_urls.add(link)

            if _is_linkedin_url(link):
                prospect = _parse_linkedin_snippet(result, business_type, location)
            else:
                prospect = _parse_web_result(result, business_type, location)

            # Skip obviously empty results
            if not prospect["name"]:
                continue

            # Try to enrich with more data from the actual page
            prospect = _enrich_from_page(prospect)
            prospects.append(prospect)
            logger.info("Found prospect: %s (%s)", prospect["name"], prospect["email"] or "no email yet")

    logger.info("Total prospects found: %d", len(prospects))
    return prospects
