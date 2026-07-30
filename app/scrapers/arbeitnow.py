"""Arbeitnow scraper — https://www.arbeitnow.com/api/job-board-api

Public unauthenticated JSON API. Returns a global mix of onsite, hybrid,
and remote jobs across roles and locations. This is the source that pulls
in onsite jobs alongside the remote-only feeds.
"""
import logging
from datetime import datetime

from .base import BaseScraper, JobPosting, http_get

logger = logging.getLogger(__name__)


def _classify(entry: dict) -> str:
    if entry.get("remote") is True:
        return "remote"
    tags = " ".join(str(t) for t in (entry.get("tags") or []))
    job_types = " ".join(str(t) for t in (entry.get("job_types") or []))
    haystack = f"{tags} {job_types}".lower()
    if "hybrid" in haystack:
        return "hybrid"
    if "remote" in haystack:
        return "remote"
    return "onsite"


class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def fetch(self):
        resp = http_get(self.endpoint, headers={"Accept": "application/json"})
        payload = resp.json() or {}
        data = payload.get("data") or []
        if not isinstance(data, list):
            logger.warning("arbeitnow: unexpected payload shape")
            return

        for item in data:
            if not isinstance(item, dict):
                continue
            slug = item.get("slug")
            if not slug:
                continue

            posted_at = None
            ts = item.get("created_at")
            if isinstance(ts, (int, float)):
                try:
                    posted_at = datetime.utcfromtimestamp(int(ts))
                except (ValueError, OSError):
                    posted_at = None

            location = (item.get("location") or "").strip() or None
            remote_type = _classify(item)
            if remote_type == "remote" and not location:
                location = "Remote"

            tags = [str(t).lower() for t in (item.get("tags") or []) if t]

            yield JobPosting(
                source=self.name,
                external_id=str(slug),
                title=(item.get("title") or "Untitled").strip(),
                company=(item.get("company_name") or "Unknown").strip(),
                url=(item.get("url") or "").strip(),
                description=(item.get("description") or "").strip(),
                location=location,
                salary=None,
                tags=tags,
                posted_at=posted_at,
                remote_type=remote_type,
            )
