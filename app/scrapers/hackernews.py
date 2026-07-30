import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseScraper, JobPosting, http_get

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://hn.algolia.com/api/v1/search"
    "?query=Ask+HN+Who+is+hiring&tags=story&hitsPerPage=5"
)
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def _clean_html(raw: str) -> str:
    if not raw:
        return ""
    text = BeautifulSoup(raw, "lxml").get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def _extract_title(text: str) -> str:
    first_line = text.split("\n", 1)[0].strip()
    # collapse pipe-delimited "Company | Role | Location | REMOTE" style headers
    if "|" in first_line:
        parts = [p.strip() for p in first_line.split("|") if p.strip()]
        return " | ".join(parts[:3]) if parts else first_line
    return first_line[:200] or "HN Hiring Post"


def _extract_company(text: str) -> str:
    first_line = text.split("\n", 1)[0].strip()
    if "|" in first_line:
        return first_line.split("|", 1)[0].strip() or "Unknown"
    if " - " in first_line:
        return first_line.split(" - ", 1)[0].strip() or "Unknown"
    return "HN"


# HN "Who is hiring" convention: posters tag with REMOTE / ONSITE / HYBRID
# (often uppercase) and/or a location like "SF" or "London".
_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)
_ONSITE_RE = re.compile(r"\b(onsite|on[-\s]?site|in[-\s]?person)\b", re.IGNORECASE)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)


def _classify_remote(text: str) -> str:
    header = text.split("\n", 1)[0]
    scope = f"{header}\n{text[:400]}"
    if _HYBRID_RE.search(scope):
        return "hybrid"
    if _REMOTE_RE.search(scope) and not _ONSITE_RE.search(scope):
        return "remote"
    if _ONSITE_RE.search(scope) and not _REMOTE_RE.search(scope):
        return "onsite"
    if _REMOTE_RE.search(scope) and _ONSITE_RE.search(scope):
        return "hybrid"
    return "unknown"


def _extract_location(text: str) -> str | None:
    first_line = text.split("\n", 1)[0].strip()
    if "|" in first_line:
        parts = [p.strip() for p in first_line.split("|") if p.strip()]
        for part in parts[1:]:  # skip company
            low = part.lower()
            if any(kw in low for kw in ("remote", "onsite", "hybrid", "eu ", "us ", "san ", "new york",
                                        "london", "berlin", "paris", "toronto", "bangalore",
                                        "mumbai", "delhi", "singapore", "amsterdam", "dublin")):
                return part[:120]
    return None


class HackerNewsScraper(BaseScraper):
    name = "hackernews"
    max_comments = 60

    def fetch(self):
        resp = http_get(SEARCH_URL, headers={"Accept": "application/json"})
        hits = resp.json().get("hits", [])
        thread_id = None
        for hit in hits:
            title = (hit.get("title") or "").lower()
            if "ask hn" in title and "who is hiring" in title:
                thread_id = hit.get("objectID")
                break
        if not thread_id:
            logger.warning("hn: no 'Who is hiring' thread found in latest results")
            return

        story_resp = http_get(ITEM_URL.format(id=thread_id), headers={"Accept": "application/json"})
        story = story_resp.json() or {}
        kids = (story.get("kids") or [])[: self.max_comments]

        for kid_id in kids:
            try:
                cresp = http_get(ITEM_URL.format(id=kid_id), headers={"Accept": "application/json"})
                comment = cresp.json() or {}
            except Exception as exc:
                logger.debug("hn: skip comment %s: %s", kid_id, exc)
                continue

            if comment.get("deleted") or comment.get("dead"):
                continue
            body = _clean_html(comment.get("text") or "")
            if not body:
                continue

            posted_at = None
            if comment.get("time"):
                posted_at = datetime.utcfromtimestamp(int(comment["time"]))

            remote_type = _classify_remote(body)
            location = _extract_location(body) or (
                "Remote" if remote_type == "remote" else None
            )

            yield JobPosting(
                source=self.name,
                external_id=str(kid_id),
                title=_extract_title(body),
                company=_extract_company(body),
                url=f"https://news.ycombinator.com/item?id={kid_id}",
                description=body,
                location=location,
                posted_at=posted_at,
                remote_type=remote_type,
            )
