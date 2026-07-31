"""The Muse scraper — https://www.themuse.com/api/public/jobs

Public unauthenticated JSON. Mixed remote + onsite, covers non-tech
categories too (marketing, sales, HR, ops, finance). We run multiple
passes to broaden coverage:

- One global pass (pages 0..N)
- India-focused passes for the major cities (Bangalore, Mumbai, Delhi,
  Hyderabad, Chennai, Pune) — Muse's `location` filter matches
  server-side, so these pull genuinely India-located jobs.

Every result's job ID is deduped in-memory before yielding, and the
orchestrator does DB-level dedup on top of that.
"""
import logging
from datetime import datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import BaseScraper, JobPosting, http_get

logger = logging.getLogger(__name__)


def _clean_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "lxml").get_text(" ", strip=True)


def _classify_remote_from_locations(locations: list[dict]) -> tuple[str, str | None]:
    """Return (remote_type, primary_location_name)."""
    if not locations:
        return "unknown", None
    names = [(loc.get("name") or "").strip() for loc in locations if isinstance(loc, dict)]
    lower_names = [n.lower() for n in names if n]
    if any("flexible / remote" in n or n == "remote" or "remote" in n for n in lower_names):
        primary = next((n for n in names if "remote" in n.lower()), names[0] if names else None)
        return "remote", primary
    return "onsite", names[0] if names else None


class TheMuseScraper(BaseScraper):
    name = "themuse"
    endpoint = "https://www.themuse.com/api/public/jobs"

    # Each entry: (pages_to_fetch, extra_query_params).
    QUERIES = [
        (4, {}),                                    # global mixed
        (3, {"location": "India"}),                 # India-wide catch-all
        (3, {"location": "Bangalore, India"}),
        (3, {"location": "Mumbai, India"}),
        (3, {"location": "Delhi, India"}),
        (3, {"location": "Hyderabad, India"}),
        (3, {"location": "Chennai, India"}),
        (3, {"location": "Pune, India"}),
    ]

    def _fetch_page(self, params: dict) -> list[dict]:
        url = f"{self.endpoint}?{urlencode(params)}"
        try:
            resp = http_get(url, headers={"Accept": "application/json"})
        except Exception as exc:
            logger.warning("themuse: %s failed: %s", url, exc)
            return []
        payload = resp.json() or {}
        results = payload.get("results") or []
        return results if isinstance(results, list) else []

    def _to_posting(self, item: dict) -> JobPosting | None:
        ext_id = str(item.get("id") or "")
        if not ext_id:
            return None

        refs = item.get("refs") or {}
        job_url = (refs.get("landing_page") or "").strip()
        if not job_url:
            return None

        company = ((item.get("company") or {}).get("name") or "Unknown").strip()

        posted_at = None
        pub = item.get("publication_date")
        if pub:
            try:
                posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
            except (ValueError, AttributeError):
                posted_at = None

        remote_type, location = _classify_remote_from_locations(item.get("locations") or [])

        tags: list[str] = []
        for cat in (item.get("categories") or []):
            if isinstance(cat, dict) and cat.get("name"):
                tags.append(str(cat["name"]).lower())
        for lvl in (item.get("levels") or []):
            if isinstance(lvl, dict) and lvl.get("name"):
                tags.append(str(lvl["name"]).lower())

        return JobPosting(
            source=self.name,
            external_id=ext_id,
            title=(item.get("name") or "Untitled").strip(),
            company=company,
            url=job_url,
            description=_clean_html(item.get("contents") or ""),
            location=location,
            salary=None,
            tags=tags,
            posted_at=posted_at,
            remote_type=remote_type,
        )

    def fetch(self):
        seen: set[str] = set()
        for max_pages, extra_params in self.QUERIES:
            for page in range(max_pages):
                params = {**extra_params, "page": page, "descending": "true"}
                results = self._fetch_page(params)
                if not results:
                    break
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    ext_id = str(item.get("id") or "")
                    if not ext_id or ext_id in seen:
                        continue
                    seen.add(ext_id)
                    posting = self._to_posting(item)
                    if posting:
                        yield posting
