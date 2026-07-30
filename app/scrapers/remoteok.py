import logging
from datetime import datetime

from .base import BaseScraper, JobPosting, http_get

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    name = "remoteok"
    endpoint = "https://remoteok.com/api"

    def fetch(self):
        resp = http_get(self.endpoint, headers={"Accept": "application/json"})
        payload = resp.json()
        if not isinstance(payload, list):
            logger.warning("remoteok: unexpected payload shape")
            return
        # first element is metadata legal notice — skip
        for item in payload[1:]:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("id") or item.get("slug") or "")
            if not ext_id:
                continue
            url = item.get("url") or item.get("apply_url") or ""
            if url and not url.startswith("http"):
                url = f"https://remoteok.com{url}"
            posted_at = None
            date_str = item.get("date")
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    posted_at = posted_at.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    posted_at = None

            salary = None
            smin, smax = item.get("salary_min"), item.get("salary_max")
            if smin and smax:
                salary = f"${int(smin):,} - ${int(smax):,}"
            elif smin:
                salary = f"${int(smin):,}+"

            yield JobPosting(
                source=self.name,
                external_id=ext_id,
                title=(item.get("position") or "").strip() or "Untitled",
                company=(item.get("company") or "Unknown").strip(),
                url=url,
                description=(item.get("description") or "").strip(),
                location=(item.get("location") or "Remote").strip() or "Remote",
                salary=salary,
                tags=[str(t).lower() for t in (item.get("tags") or []) if t],
                posted_at=posted_at,
                remote_type="remote",
            )
