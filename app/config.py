import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///job_tracker.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    SCRAPE_TIMEOUT = int(os.environ.get("SCRAPE_TIMEOUT", "15"))
    SCRAPE_USER_AGENT = os.environ.get(
        "SCRAPE_USER_AGENT",
        "JobTracker/1.0 (+https://github.com/local)",
    )
    SCRAPE_MAX_RETRIES = int(os.environ.get("SCRAPE_MAX_RETRIES", "2"))
    SCRAPE_BACKOFF_SECONDS = float(os.environ.get("SCRAPE_BACKOFF_SECONDS", "1.5"))
