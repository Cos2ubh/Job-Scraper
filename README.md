# Job Tracker

A local-first job scraper and application tracker. Aggregates remote and onsite roles from public feeds, scores them against your resume with a TF-IDF matcher, and gives you a Kanban board plus application analytics — all offline, no API keys, no login required.

## Features

- **Dashboard** — remote and onsite jobs from RemoteOK, WeWorkRemotely, Arbeitnow, and Hacker News "Who is hiring". "Scrape Now" trigger, search/filter by title, company, remote type, and date.
- **Kanban** — five-column board (To Apply → Applied → Interviewing → Offer → Rejected). Drag-and-drop or dropdown to move cards. Manual add form.
- **Quick Save** — one-click "Track This Job" clones a scraped job into your Kanban.
- **Profile** — paste resume text and skill keywords. Every scraped job gets a Match Score % on the dashboard.
- **Analytics** — total-applications-over-time bar chart, status doughnut, interview and offer conversion rates, top companies.

## Stack

- Backend: Python 3.10+, Flask 3, SQLAlchemy 2, SQLite
- Scraping: `requests`, `beautifulsoup4`, `lxml`, `feedparser` — hitting only public JSON/RSS feeds
- Matching: pure-Python TF-IDF + cosine similarity (no ML dependencies)
- Frontend: HTML5, Tailwind CSS (CDN), Chart.js (CDN), vanilla JS
- Data sources (all unauthenticated public):
  - RemoteOK JSON: `https://remoteok.com/api` (remote)
  - WeWorkRemotely RSS: category feeds under `https://weworkremotely.com/categories/…` (remote)
  - Arbeitnow JSON: `https://www.arbeitnow.com/api/job-board-api` (remote + onsite, global)
  - Hacker News "Who is hiring" via Algolia HN Search + Firebase HN item API (remote + onsite)

## Setup

Run from PowerShell in the project root:

```powershell
# 1. Create + activate a venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env template
Copy-Item .env.example .env

# 4. Run
python run.py
```

Open http://127.0.0.1:5000 in your browser. The SQLite database `job_tracker.db` is created automatically on first run.

## First run flow

1. Go to **Profile**, paste your resume, add comma-separated skill keywords, save.
2. Go to **Dashboard**, click **Scrape Now**. Fresh jobs appear with match scores.
3. Click **Track This Job** on anything interesting. It lands in the Kanban's "To Apply" column.
4. Move cards through your pipeline (drag or dropdown).
5. Check **Analytics** to watch your conversion rate.

## Project layout

```
job-tracker/
├── run.py                       # entrypoint
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # env-driven config
│   ├── database.py              # SQLAlchemy instance
│   ├── models.py                # ScrapedJob, TrackedJob, Profile
│   ├── matching.py              # TF-IDF match-score engine
│   ├── routes/                  # API + page blueprints
│   └── scrapers/                # per-source scrapers + orchestrator
├── static/                      # css, vanilla JS
└── templates/                   # Jinja2 templates
```

## API summary

| Method | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| POST   | `/api/scrape`                         | Run all scrapers, upsert into DB. |
| GET    | `/api/jobs?q=&company=&days=&remote_type=` | List scraped jobs (filter by remote/onsite/hybrid) with match scores. |
| GET    | `/api/tracker`                        | List tracked (Kanban) jobs. |
| POST   | `/api/tracker`                        | Add a tracked job manually. |
| POST   | `/api/tracker/from-scraped/<id>`      | Quick-save a scraped job to Kanban. |
| PATCH  | `/api/tracker/<id>`                   | Update status / fields. |
| DELETE | `/api/tracker/<id>`                   | Remove a tracked job. |
| GET    | `/api/profile`                        | Get resume + keywords. |
| PUT    | `/api/profile`                        | Save resume + keywords. |
| GET    | `/api/analytics`                      | KPIs + time-series + status breakdown. |

## Error handling

- All scraper HTTP calls retry with exponential backoff (config: `SCRAPE_MAX_RETRIES`, `SCRAPE_BACKOFF_SECONDS`) and honor a timeout (`SCRAPE_TIMEOUT`).
- Rate-limit responses (HTTP 429) trigger the same retry path.
- Individual scraper failures are isolated — orchestrator logs and continues, so one flaky source doesn't kill the batch.
- All routes return JSON errors via a global `HTTPException` handler; uncaught exceptions log a stack trace and return a 500 JSON body.
- Frontend surfaces every error via toast notifications.

## Constraints honored

- Zero paid APIs, zero foundation-model calls, zero authenticated scraping.
- Match scoring runs entirely on your machine in pure Python.
- All data (jobs, applications, profile) lives in a local SQLite file — nothing leaves the box.
