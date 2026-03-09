"""
ai_engine.py – Generate personalised pitch emails using OpenAI.

Each email is crafted specifically for the prospect based on:
  • Their business type and description
  • Our studio's name, website, and portfolio
  • A professional, concise tone that feels hand-written, not templated
"""

from __future__ import annotations

import logging

from openai import OpenAI

from client_finder import config

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pitch_email(prospect: dict[str, str]) -> tuple[str, str]:
    """
    Generate a personalised pitch email for *prospect*.

    Returns
    -------
    (subject, body) – both as plain text strings.
    """
    system_prompt = (
        f"You are a business development specialist at {config.STUDIO_NAME}, "
        "a premium design studio that helps businesses build remarkable brands. "
        "Your services include website design, logo design, brand identity, "
        "UI/UX design, and all creative design work. "
        "Write professional, warm, and concise outreach emails that feel genuinely "
        "personalised—never generic or salesy. "
        "Always end with a clear, low-friction call-to-action (e.g., a 15-minute call)."
    )

    user_prompt = _build_user_prompt(prospect)

    logger.info("Generating pitch email for %s via OpenAI…", prospect.get("name"))
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=600,
    )

    raw = response.choices[0].message.content or ""
    subject, body = _parse_response(raw, prospect)
    return subject, body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_prompt(prospect: dict[str, str]) -> str:
    name = prospect.get("name") or "there"
    biz_type = prospect.get("business_type") or "business"
    description = prospect.get("description") or ""
    location = prospect.get("location") or ""
    website = prospect.get("website") or prospect.get("linkedin_url") or ""

    lines = [
        f"Write a personalised outreach email to a potential client.",
        f"",
        f"Prospect details:",
        f"  - Name: {name}",
        f"  - Business type: {biz_type}",
    ]
    if location:
        lines.append(f"  - Location: {location}")
    if description:
        lines.append(f"  - About them (from their web presence): {description[:400]}")
    if website:
        lines.append(f"  - Their website/LinkedIn: {website}")

    lines += [
        f"",
        f"Our studio:",
        f"  - Studio name: {config.STUDIO_NAME}",
    ]
    if config.STUDIO_WEBSITE:
        lines.append(f"  - Our website: {config.STUDIO_WEBSITE}")
    if config.STUDIO_PORTFOLIO:
        lines.append(f"  - Our portfolio: {config.STUDIO_PORTFOLIO}")

    lines += [
        f"",
        f"Format the email exactly like this:",
        f"SUBJECT: <email subject line>",
        f"",
        f"<email body, addressed to the prospect>",
    ]

    return "\n".join(lines)


def _parse_response(raw: str, prospect: dict[str, str]) -> tuple[str, str]:
    """Split the raw OpenAI response into (subject, body)."""
    lines = raw.strip().splitlines()
    subject = ""
    body_lines: list[str] = []
    in_body = False

    for line in lines:
        if line.upper().startswith("SUBJECT:") and not in_body:
            subject = line[len("SUBJECT:"):].strip()
        elif subject and not in_body and line.strip() == "":
            in_body = True
        elif in_body or subject:
            body_lines.append(line)

    if not subject:
        subject = f"Elevate {prospect.get('name', 'Your Brand')} with World-Class Design"

    body = "\n".join(body_lines).strip()
    if not body:
        body = raw.strip()

    return subject, body
