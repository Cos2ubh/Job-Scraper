import hashlib
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup

from .base import BaseScraper, JobPosting, http_get

logger = logging.getLogger(__name__)

FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
]


def _clean_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "lxml").get_text(" ", strip=True)


def _parse_title(title: str) -> tuple[str, str, str | None]:
    # WWR title format: "Company: Position" or "Company: Position (Location)"
    company, position, location = "Unknown", title, None
    if ":" in title:
        company_part, rest = title.split(":", 1)
        company = company_part.strip()
        position = rest.strip()
    if "(" in position and position.endswith(")"):
        pos_only, loc_part = position.rsplit("(", 1)
        position = pos_only.strip()
        location = loc_part.rstrip(")").strip()
    return company, position, location


class WeWorkRemotelyScraper(BaseScraper):
    name = "weworkremotely"

    def fetch(self):
        seen: set[str] = set()
        for feed_url in FEEDS:
            try:
                resp = http_get(feed_url)
            except Exception as exc:
                logger.warning("wwr: failed feed %s: %s", feed_url, exc)
                continue

            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries:
                link = entry.get("link") or ""
                if not link:
                    continue
                ext_id = hashlib.sha1(link.encode()).hexdigest()[:20]
                if ext_id in seen:
                    continue
                seen.add(ext_id)

                company, position, location = _parse_title(entry.get("title", ""))
                description = _clean_html(entry.get("summary", ""))

                posted_at = None
                if entry.get("published"):
                    try:
                        posted_at = parsedate_to_datetime(entry.published).replace(tzinfo=None)
                    except (TypeError, ValueError):
                        posted_at = None

                yield JobPosting(
                    source=self.name,
                    external_id=ext_id,
                    title=position or "Untitled",
                    company=company or "Unknown",
                    url=link,
                    description=description,
                    location=location or "Remote",
                    posted_at=posted_at,
                    remote_type="remote",
                )
