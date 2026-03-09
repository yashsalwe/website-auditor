"""
sheets.py – Google Sheets integration via gspread.

Sheet layout
------------
Row 1 is always the header row.  Every subsequent row is one prospect.

Columns (in order):
  A  Name
  B  Business Type
  C  Website
  D  Email
  E  Phone
  F  LinkedIn URL
  G  Location
  H  Description
  I  Source URL
  J  Email Sent   (populated as "Yes" once pitch email is dispatched)
"""

from __future__ import annotations

import logging
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from client_finder import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Name",
    "Business Type",
    "Website",
    "Email",
    "Phone",
    "LinkedIn URL",
    "Location",
    "Description",
    "Source URL",
    "Email Sent",
]

# Map each header to its zero-based column index (for fast lookup)
_COL_INDEX = {h: i for i, h in enumerate(HEADERS)}


# ---------------------------------------------------------------------------
# Worksheet helpers
# ---------------------------------------------------------------------------

def _get_worksheet() -> gspread.Worksheet:
    """Return the first worksheet, creating the header row if needed."""
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    ws = sheet.sheet1

    # Ensure header row exists
    existing = ws.row_values(1)
    if existing != HEADERS:
        ws.clear()
        ws.append_row(HEADERS, value_input_option="RAW")
        logger.info("Sheet initialised with header row.")

    return ws


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_prospects(prospects: list[dict[str, str]]) -> list[int]:
    """
    Append *prospects* to the Google Sheet.

    Duplicates (same email OR same LinkedIn URL already in the sheet) are
    skipped to avoid spamming the same contact twice.

    Returns
    -------
    list of 1-based row numbers for each newly inserted prospect.
    """
    ws = _get_worksheet()

    # Fetch existing data for de-duplication
    existing_emails: set[str] = set()
    existing_linkedin: set[str] = set()
    all_rows = ws.get_all_values()
    for row in all_rows[1:]:  # skip header
        email_val = row[_COL_INDEX["Email"]].strip().lower() if len(row) > _COL_INDEX["Email"] else ""
        li_val = row[_COL_INDEX["LinkedIn URL"]].strip().lower() if len(row) > _COL_INDEX["LinkedIn URL"] else ""
        if email_val:
            existing_emails.add(email_val)
        if li_val:
            existing_linkedin.add(li_val)

    new_row_numbers: list[int] = []
    next_row = len(all_rows) + 1  # 1-based row number after last existing row

    rows_to_append: list[list[str]] = []
    for p in prospects:
        p_email = p.get("email", "").strip().lower()
        p_li = p.get("linkedin_url", "").strip().lower()

        if (p_email and p_email in existing_emails) or (p_li and p_li in existing_linkedin):
            logger.debug("Skipping duplicate prospect: %s", p.get("name"))
            continue

        row = _prospect_to_row(p)
        rows_to_append.append(row)
        new_row_numbers.append(next_row)
        next_row += 1

        if p_email:
            existing_emails.add(p_email)
        if p_li:
            existing_linkedin.add(p_li)

    if rows_to_append:
        ws.append_rows(rows_to_append, value_input_option="RAW")
        logger.info("Saved %d new prospects to Google Sheet.", len(rows_to_append))
    else:
        logger.info("No new prospects to save (all duplicates).")

    return new_row_numbers


def mark_email_sent(row_number: int) -> None:
    """Set the 'Email Sent' cell in *row_number* to 'Yes'."""
    ws = _get_worksheet()
    col_letter = _col_letter(_COL_INDEX["Email Sent"])
    ws.update_acell(f"{col_letter}{row_number}", "Yes")
    logger.info("Marked row %d as email sent.", row_number)


def get_all_prospects() -> list[dict[str, str]]:
    """Return all prospects from the sheet as a list of dicts."""
    ws = _get_worksheet()
    records = ws.get_all_records()
    return [dict(r) for r in records]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prospect_to_row(p: dict[str, str]) -> list[str]:
    """Convert a prospect dict to a list aligned with HEADERS."""
    key_map = {
        "Name": "name",
        "Business Type": "business_type",
        "Website": "website",
        "Email": "email",
        "Phone": "phone",
        "LinkedIn URL": "linkedin_url",
        "Location": "location",
        "Description": "description",
        "Source URL": "source_url",
        "Email Sent": "email_sent",
    }
    return [str(p.get(key_map[h], "")) for h in HEADERS]


def _col_letter(zero_based_index: int) -> str:
    """Convert a zero-based column index to an A1 column letter (A-Z only)."""
    return chr(ord("A") + zero_based_index)
