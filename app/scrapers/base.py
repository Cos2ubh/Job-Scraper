import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

import requests
from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    description: str = ""
    location: str | None = None
    salary: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: datetime | None = None
    remote_type: str = "unknown"  # "remote" | "onsite" | "hybrid" | "unknown"


class ScraperError(Exception):
    pass


def http_get(url: str, headers: dict | None = None) -> requests.Response:
    """GET with retry, timeout, and User-Agent from app config."""
    cfg = current_app.config
    session_headers = {
        "User-Agent": cfg["SCRAPE_USER_AGENT"],
        "Accept": "*/*",
    }
    if headers:
        session_headers.update(headers)

    max_retries = cfg["SCRAPE_MAX_RETRIES"]
    backoff = cfg["SCRAPE_BACKOFF_SECONDS"]
    timeout = cfg["SCRAPE_TIMEOUT"]

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=session_headers, timeout=timeout)
            if resp.status_code == 429:
                raise ScraperError(f"Rate limited (429) fetching {url}")
            resp.raise_for_status()
            return resp
        except (requests.RequestException, ScraperError) as exc:
            last_exc = exc
            wait = backoff * (2 ** attempt)
            logger.warning(
                "fetch failed (attempt %d/%d) for %s: %s — retrying in %.1fs",
                attempt + 1, max_retries + 1, url, exc, wait,
            )
            if attempt < max_retries:
                time.sleep(wait)
    raise ScraperError(f"Failed to fetch {url} after {max_retries + 1} attempts: {last_exc}")


class BaseScraper:
    name: str = "base"

    def fetch(self) -> Iterable[JobPosting]:
        raise NotImplementedError

    def safe_fetch(self) -> list[JobPosting]:
        try:
            return list(self.fetch())
        except Exception:
            logger.exception("scraper %s failed", self.name)
            return []
