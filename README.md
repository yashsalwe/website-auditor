# Website Auditor – AI Client Finder

> **Integrating AI into an agency isn't just about adding new software; it's about understanding the people who use it.**

This repository now contains two things:

1. A conversational, role-specific questionnaire for digital marketing teams to discover how AI can improve their daily workflows.
2. **An AI-powered client-prospecting agent** that helps a design studio automatically find potential clients, personalise outreach emails, and track everything in Google Sheets.

---

## AI Client Finder Agent

### What it does

| Step | What happens |
|------|--------------|
| 1 | You enter a **business type**, **location**, and **keywords** |
| 2 | The agent searches Google (via SerpAPI) for matching companies and LinkedIn profiles |
| 3 | Each result is enriched (email, phone, description) by visiting their public web pages |
| 4 | All prospects are saved to a **Google Sheet** (duplicates skipped automatically) |
| 5 | A **personalised pitch email** is generated for each prospect using **OpenAI GPT-4o-mini** |
| 6 | The email is sent via **SMTP** |
| 7 | The Google Sheet is updated with **"Email Sent = Yes"** for each successfully contacted prospect |

### Project structure

```
client_finder/
├── __init__.py
├── config.py        ← loads & validates all env vars
├── scraper.py       ← SerpAPI + BeautifulSoup prospecting
├── sheets.py        ← Google Sheets read/write (gspread)
├── ai_engine.py     ← OpenAI personalised email generation
├── emailer.py       ← SMTP email sender
├── main.py          ← CLI entry point / pipeline orchestrator
└── credentials/     ← place your service_account.json here (git-ignored)

tests/
├── test_scraper.py
├── test_sheets.py
├── test_ai_engine.py
└── test_emailer.py
```

### Prerequisites

| Service | Why it's needed | How to get it |
|---------|----------------|---------------|
| [OpenAI API key](https://platform.openai.com/api-keys) | Generate personalised pitch emails | Sign up at platform.openai.com |
| [SerpAPI key](https://serpapi.com/) | Search Google for LinkedIn profiles and web pages | Free plan available |
| [Google Service Account](https://console.cloud.google.com/) | Read/write Google Sheets | Create a project → enable Sheets API → create a service-account key |
| SMTP credentials | Send emails | Gmail app password or any SMTP provider |

### Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/yashsalwe/website-auditor.git
cd website-auditor

# 2. Install Python dependencies (Python 3.10+ recommended)
pip install -r requirements.txt

# 3. Create your .env file
cp .env.example .env
# Edit .env and fill in all API keys and credentials

# 4. Place your Google service-account JSON key
mkdir -p client_finder/credentials
cp /path/to/your-service-account.json client_finder/credentials/service_account.json
# Make sure GOOGLE_SERVICE_ACCOUNT_JSON in .env points to this path

# 5. Share your Google Sheet with the service-account email
#    (found in the JSON file as "client_email")
```

### Usage

```bash
python -m client_finder.main
```

You will be prompted to enter:

```
1. Target business type (e.g. 'restaurant', 'e-commerce startup'):  restaurant
2. Location (e.g. 'Mumbai', 'New York'):  Mumbai
3. Keywords (comma-separated, e.g. 'new brand, no website, startup'):  new brand, no online presence
4. Maximum prospects to find [default 20]:  15
```

The agent then runs automatically and prints progress to the console.

### Google Sheet columns

| A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|
| Name | Business Type | Website | Email | Phone | LinkedIn URL | Location | Description | Source URL | **Email Sent** |

### Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```

### Environment variables reference

See [`.env.example`](.env.example) for the full list.  The most important ones:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI secret key |
| `SERPAPI_API_KEY` | SerpAPI key for Google searches |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to service-account JSON file |
| `GOOGLE_SHEET_ID` | ID of the target Google Spreadsheet |
| `SMTP_USER` / `SMTP_PASSWORD` | Email credentials |
| `STUDIO_NAME` | Your studio name (used in pitch emails) |
| `STUDIO_WEBSITE` | Your studio website URL |
| `STUDIO_PORTFOLIO` | Your portfolio URL |

### Note on LinkedIn

Direct scraping of LinkedIn violates their Terms of Service.  This agent uses **SerpAPI's Google Search** with `site:linkedin.com` queries to surface publicly indexed profile snippets, which is a compliant approach.

---

*Built for design studios that want to spend less time prospecting and more time designing.*
