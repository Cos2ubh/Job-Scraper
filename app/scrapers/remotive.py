"""Remotive scraper — https://remotive.com/api/remote-jobs

Public unauthenticated JSON. Remote-only, wide category coverage
(software, marketing, sales, customer support, design, product, etc.).
"""
import logging
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseScraper, JobPosting, http_get

logger = logging.getLogger(__name__)


def _clean_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "lxml").get_text(" ", strip=True)


class RemotiveScraper(BaseScraper):
    name = "remotive"
    endpoint = "https://remotive.com/api/remote-jobs"

    def fetch(self):
        resp = http_get(self.endpoint, headers={"Accept": "application/json"})
        payload = resp.json() or {}
        jobs = payload.get("jobs") or []
        if not isinstance(jobs, list):
            logger.warning("remotive: unexpected payload shape")
            return

        for item in jobs:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("id") or "")
            if not ext_id:
                continue

            posted_at = None
            pub = item.get("publication_date")
            if pub:
                try:
                    posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    posted_at = None

            tags = [str(t).lower() for t in (item.get("tags") or []) if t]
            if item.get("category"):
                tags.append(str(item["category"]).lower())

            location = (item.get("candidate_required_location") or "Remote").strip() or "Remote"

            yield JobPosting(
                source=self.name,
                external_id=ext_id,
                title=(item.get("title") or "Untitled").strip(),
                company=(item.get("company_name") or "Unknown").strip(),
                url=(item.get("url") or "").strip(),
                description=_clean_html(item.get("description") or ""),
                location=location,
                salary=(item.get("salary") or None) or None,
                tags=tags,
                posted_at=posted_at,
                remote_type="remote",
            )
