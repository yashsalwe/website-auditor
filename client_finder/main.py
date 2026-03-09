"""
main.py – Entry point for the AI Client Finder agent.

Usage
-----
    python -m client_finder.main

The script prompts the user for:
  1. Business type  (e.g. "restaurant", "e-commerce startup")
  2. Location       (e.g. "Mumbai", "London")
  3. Keywords       (comma-separated, e.g. "no website, new brand, small business")

Then it:
  1. Scrapes the web + LinkedIn for matching prospects
  2. Saves them to Google Sheets (duplicates skipped)
  3. Generates a personalised pitch email for each prospect (via OpenAI)
  4. Sends the email via SMTP
  5. Updates the Google Sheet to mark "Email Sent = Yes"
"""

from __future__ import annotations

import logging
import sys

from client_finder import ai_engine, emailer, scraper, sheets

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt(question: str) -> str:
    try:
        return input(question).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def _get_user_inputs() -> tuple[str, str, list[str], int]:
    print("\n===== AI Client Finder – Design Studio Prospecting Agent =====\n")

    business_type = ""
    while not business_type:
        business_type = _prompt("1. Target business type (e.g. 'restaurant', 'e-commerce startup'): ")
        if not business_type:
            print("   [!] Business type cannot be empty.")

    location = ""
    while not location:
        location = _prompt("2. Location (e.g. 'Mumbai', 'New York'): ")
        if not location:
            print("   [!] Location cannot be empty.")

    keywords_raw = _prompt("3. Keywords (comma-separated, e.g. 'new brand, no website, startup'): ")
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    max_results_raw = _prompt("4. Maximum prospects to find [default 20]: ")
    try:
        max_results = int(max_results_raw) if max_results_raw else 20
    except ValueError:
        max_results = 20

    print(
        f"\n✔ Searching for up to {max_results} '{business_type}' prospects in '{location}'"
        + (f" with keywords: {keywords}" if keywords else "")
        + "\n"
    )
    return business_type, location, keywords, max_results


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    business_type: str,
    location: str,
    keywords: list[str],
    max_results: int = 20,
) -> None:
    """Execute the full client-finding pipeline."""

    # ── Step 1: Find prospects ───────────────────────────────────────────────
    logger.info("STEP 1/4 – Searching for prospects…")
    prospects = scraper.find_prospects(business_type, location, keywords, max_results)

    if not prospects:
        logger.warning("No prospects found. Try broader keywords or a different location.")
        return

    print(f"\n🔍  Found {len(prospects)} prospect(s).\n")

    # ── Step 2: Save to Google Sheets ────────────────────────────────────────
    logger.info("STEP 2/4 – Saving prospects to Google Sheets…")
    row_numbers = sheets.save_prospects(prospects)

    if not row_numbers:
        logger.info("All prospects were already in the sheet.")
        print("ℹ  All prospects were already in the sheet – no duplicates saved.\n")
        return

    print(f"📊  Saved {len(row_numbers)} new prospect(s) to Google Sheets.\n")

    # ── Steps 3 & 4: Generate + send personalised emails ────────────────────
    logger.info("STEP 3/4 – Generating and sending pitch emails…")
    sent_count = 0
    skipped_count = 0

    # row_numbers aligns with the newly inserted prospects (filtering out dupes)
    # row_numbers corresponds to the first len(row_numbers) non-duplicate prospects
    new_prospects = prospects[: len(row_numbers)]

    for prospect, row_num in zip(new_prospects, row_numbers):
        email_addr = prospect.get("email", "")

        if not email_addr:
            logger.warning(
                "No email for '%s' – generating email anyway for reference but not sending.",
                prospect.get("name"),
            )
            skipped_count += 1
            continue

        # Generate personalised subject + body
        subject, body = ai_engine.generate_pitch_email(prospect)

        # Send the email
        success = emailer.send_pitch_email(
            to_email=email_addr,
            to_name=prospect.get("name", ""),
            subject=subject,
            body=body,
        )

        # ── Step 4: Update sheet ─────────────────────────────────────────────
        if success:
            sheets.mark_email_sent(row_num)
            sent_count += 1
        else:
            skipped_count += 1

    print(
        f"\n✉  Emails sent: {sent_count}  |  Skipped (no email / send failure): {skipped_count}\n"
    )
    logger.info("STEP 4/4 – Google Sheet updated. Pipeline complete.")
    print("✅  All done! Check your Google Sheet for the full prospect list.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    business_type, location, keywords, max_results = _get_user_inputs()
    run_pipeline(business_type, location, keywords, max_results)


if __name__ == "__main__":
    main()
