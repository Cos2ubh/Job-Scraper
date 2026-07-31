# Job-Scraper

**A local-first job search command center.** Scrapes fresh remote and onsite roles from four public feeds every time you hit "Scrape Now", scores each one against your resume with a TF-IDF matcher, and lets you drag them across a five-column Kanban to track your pipeline end-to-end. Everything runs on your machine — no accounts, no API keys, no third-party services touching your data.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-CDN-38BDF8?logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Why this exists

Job hunting spreads across a dozen tabs — RemoteOK, WeWorkRemotely, Hacker News "Who is hiring", plus a spreadsheet somewhere trying to remember who ghosted you. Job-Scraper collapses all of that into a single Flask app:

- One page to **discover** fresh roles filtered by remote/onsite/hybrid.
- One page to **track** where each application stands.
- One page to see your **conversion rate**, so you actually know if your pipeline is working.
- A **pure-Python TF-IDF matcher** that ranks scraped jobs against a resume you paste once. No LLM calls, no embeddings API, no vendor lock-in.

Built as a portfolio project to demonstrate end-to-end fluency: SQLAlchemy modeling, retry-aware scraping, Flask blueprints, information retrieval, drag-and-drop UI, chart-based analytics.

---

## Features

**Dashboard**
- Aggregates jobs from six public, unauthenticated sources — global remote, onsite worldwide, and onsite India
- Full-text search across title, location, description, and tags (type "Bangalore" to filter India jobs)
- Filter by company, date posted, remote/onsite/hybrid, experience level, category
- Colored badges per role (category · remote type · experience · match %)
- Hides subscription-only listings by default; a checkbox brings them back at the bottom with a red "Subscription" badge
- Per-job **Match %** once your profile is set

**Kanban tracker**
- Five columns: To Apply → Applied → Interviewing → Offer → Rejected
- HTML5 drag-and-drop between columns (dropdown fallback on every card)
- Manual add-job modal (title, company, salary, URL, notes, date applied)
- **Quick Save** button on every scraped job — one click sends it to "To Apply"

**Profile-based match scoring**
- Paste raw resume text and a comma-separated skills list
- Pure-Python TF-IDF + cosine similarity (no sklearn dependency)
- Explicit keywords get 2× weight in the resume vector plus a bonus for direct hits in the job posting

**Analytics**
- Total tracked, applied, interview rate, offer rate — as KPI cards
- Applications over the last 30 days (bar chart)
- Status breakdown (doughnut)
- Top-5 companies you've applied to

---

## Tech stack

- **Backend:** Python 3.10+, Flask 3, SQLAlchemy 2, SQLite (local file)
- **Scraping:** `requests` + retry/backoff, `beautifulsoup4`, `lxml`, `feedparser`
- **Matching:** hand-rolled TF-IDF with cosine similarity in `app/matching.py`
- **Frontend:** Jinja2 templates, Tailwind CSS (CDN), Chart.js (CDN), vanilla JS
- **Zero external services:** no API keys, no OAuth, no LLMs, no analytics beacons

## Data sources

| Source          | Access                                        | Type                                  |
| --------------- | --------------------------------------------- | ------------------------------------- |
| RemoteOK        | `https://remoteok.com/api`                    | Public JSON, remote                   |
| WeWorkRemotely  | `weworkremotely.com/…/*.rss`                  | Public RSS, remote                    |
| Arbeitnow       | `arbeitnow.com/api/job-board-api`             | Public JSON, remote + onsite (global) |
| Remotive        | `remotive.com/api/remote-jobs`                | Public JSON, remote (broad categories)|
| The Muse        | `themuse.com/api/public/jobs` (multi-pass)    | Public JSON, remote + onsite; global + India cities (Bangalore, Mumbai, Delhi, Hyderabad, Chennai, Pune) |
| Hacker News     | Algolia HN Search + HN Firebase API           | Public JSON, remote + onsite          |

All six are unauthenticated public endpoints. Every request goes through a shared HTTP wrapper with configurable timeout, exponential backoff, and 429 handling.

**Note on India coverage.** The major Indian job sites (Naukri, LinkedIn, Indeed India, Foundit, Instahyre, Hirect) require authentication or actively block anonymous scrapers with Cloudflare Turnstile / CAPTCHAs, so they can't be integrated under the zero-auth constraint. India-focused onsite coverage comes primarily from The Muse's city-specific location passes.

---

## Setup

```powershell
# clone
git clone https://github.com/Cos2ubh/Job-Scraper.git
cd Job-Scraper

# venv + deps
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# env
Copy-Item .env.example .env

# run
python run.py
```

Then open **http://127.0.0.1:5000/** in your browser. The SQLite database (`job_tracker.db`) is created automatically on first run.

Bash equivalents (macOS/Linux):

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## First-run flow

1. Open **Profile** → paste your resume + comma-separated keywords → **Save**.
2. Open **Dashboard** → click **Scrape Now**. ~15–30s later, jobs load with a Match % badge and a Remote/Onsite/Hybrid tag on each card.
3. Use the filters to narrow by remote type, date, company, or free-text query.
4. Click **Track This Job** on anything interesting — it lands in the Kanban's "To Apply" column.
5. Drag cards across columns as you progress. When you move a job to "Applied", `date_applied` auto-populates.
6. Check **Analytics** to see your conversion rate and 30-day timeline.

---

## Project layout

```
Job-Scraper/
├── run.py                       # entrypoint (python run.py)
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py              # Flask app factory + blueprint registration
│   ├── config.py                # env-driven config
│   ├── database.py              # SQLAlchemy instance
│   ├── migrations.py            # lightweight startup migrations (idempotent)
│   ├── models.py                # ScrapedJob, TrackedJob, Profile
│   ├── matching.py              # TF-IDF match-score engine (pure Python)
│   ├── routes/
│   │   ├── pages.py             # HTML page routes
│   │   ├── jobs_api.py          # /api/jobs, /api/scrape
│   │   ├── tracker_api.py       # /api/tracker CRUD + quick-save
│   │   ├── profile_api.py       # /api/profile
│   │   └── analytics_api.py     # /api/analytics
│   └── scrapers/
│       ├── base.py              # shared HTTP session, retries, JobPosting dataclass
│       ├── remoteok.py          # RemoteOK JSON
│       ├── weworkremotely.py    # WWR RSS
│       ├── arbeitnow.py         # Arbeitnow JSON (remote + onsite)
│       ├── hackernews.py        # HN "Who is hiring" via Algolia + HN Firebase
│       └── orchestrator.py      # run all sources, dedupe, persist
├── static/
│   ├── css/custom.css
│   └── js/
│       ├── common.js            # shared api wrapper + toast helpers
│       ├── dashboard.js
│       ├── kanban.js
│       ├── profile.js
│       └── analytics.js
└── templates/
    ├── base.html                # nav, Tailwind + Chart.js CDN
    ├── dashboard.html
    ├── kanban.html
    ├── profile.html
    └── analytics.html
```

## API reference

| Method | Path                                       | Purpose |
| ------ | ------------------------------------------ | ------- |
| POST   | `/api/scrape`                              | Run all scrapers, upsert into DB. Returns per-source counts. |
| GET    | `/api/jobs?q=&company=&days=&remote_type=` | List scraped jobs (filter by remote/onsite/hybrid) with match scores. |
| GET    | `/api/tracker`                             | List all tracked jobs. |
| POST   | `/api/tracker`                             | Add a tracked job manually. |
| POST   | `/api/tracker/from-scraped/<id>`           | Quick-save a scraped job to "To Apply". |
| PATCH  | `/api/tracker/<id>`                        | Update status or any field. |
| DELETE | `/api/tracker/<id>`                        | Remove a tracked job. |
| GET    | `/api/profile`                             | Get resume text + keywords. |
| PUT    | `/api/profile`                             | Save resume text + keywords. |
| GET    | `/api/analytics`                           | KPIs + 30-day timeline + status breakdown. |

## How match scoring works

Instead of an embedding API, `app/matching.py` implements a lightweight retrieval pipeline in ~90 lines of pure Python:

1. **Tokenize** the resume and each job's `title + tags + description` (alphanumeric + `+#.` for tokens like `c++`, `c#`, `node.js`).
2. **Filter stopwords** (a curated list tuned for job descriptions — drops "team", "experience", "candidate", etc. that add noise).
3. **Explicit-keyword boost**: every skill in your comma-separated keyword list is added to the resume vector twice, so `python, react, aws` weighs heavier than words that just happen to appear once.
4. **TF-IDF** — compute term frequencies per doc, IDF across the batch of jobs currently being shown.
5. **Cosine similarity** between the resume vector and each job vector.
6. **Keyword-overlap bonus**: add up to +25 points when the job posting explicitly mentions your listed skills.
7. Squash to a 0-100 score, render as a colored badge (green ≥65, yellow ≥35, red below).

Trade-off: TF-IDF misses semantic similarity (Python and Django won't cluster), but it's transparent, zero-dependency, and runs client-side on your CPU in milliseconds.

## Error handling

- **HTTP layer** (`app/scrapers/base.py`) — every scraper request has a timeout, retries with exponential backoff, and explicit 429 rate-limit handling.
- **Per-scraper isolation** — a broken source logs a stack trace and returns an empty list rather than killing the whole scrape.
- **Per-upsert isolation** — malformed job records are logged and skipped; the batch commits per source with rollback on failure.
- **API layer** — global `HTTPException` handler serializes errors to JSON; uncaught exceptions log the full trace and return a JSON 500.
- **Frontend** — every `fetch` goes through a wrapper that surfaces network and HTTP errors as toast notifications.

## Constraints honored

- Zero paid APIs, zero LLM calls, zero authenticated scraping.
- All data (jobs, applications, profile, resume text) lives in a local SQLite file — nothing leaves your machine.
- Every dependency is open-source and pinned in `requirements.txt`.

## License

[MIT](LICENSE) — do whatever you want with the code, no warranty.
