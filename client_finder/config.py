"""
config.py – Load and expose all configuration/environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Return env var *key* or raise a descriptive error."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Copy .env.example to .env and fill in all values."
        )
    return value


# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = _require("OPENAI_API_KEY")

# ── SerpAPI ───────────────────────────────────────────────────────────────────
SERPAPI_API_KEY: str = _require("SERPAPI_API_KEY")

# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_SERVICE_ACCOUNT_JSON: str = _require("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID: str = _require("GOOGLE_SHEET_ID")

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = _require("SMTP_USER")
SMTP_PASSWORD: str = _require("SMTP_PASSWORD")
EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Design Studio")

# ── Studio info ───────────────────────────────────────────────────────────────
STUDIO_NAME: str = os.getenv("STUDIO_NAME", "Our Design Studio")
STUDIO_WEBSITE: str = os.getenv("STUDIO_WEBSITE", "")
STUDIO_PORTFOLIO: str = os.getenv("STUDIO_PORTFOLIO", "")
