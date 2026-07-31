import logging
from datetime import datetime

from ..accessibility import classify_accessibility
from ..classifier import classify_category, classify_experience
from ..database import db
from ..models import ScrapedJob
from .arbeitnow import ArbeitnowScraper
from .base import JobPosting
from .hackernews import HackerNewsScraper
from .remoteok import RemoteOKScraper
from .weworkremotely import WeWorkRemotelyScraper

logger = logging.getLogger(__name__)

SCRAPERS = [
    RemoteOKScraper(),
    WeWorkRemotelyScraper(),
    ArbeitnowScraper(),
    HackerNewsScraper(),
]


def _upsert(posting: JobPosting) -> tuple[bool, bool]:
    """Insert or update. Returns (inserted, updated)."""
    existing = ScrapedJob.query.filter_by(
        source=posting.source, external_id=posting.external_id
    ).first()

    experience_level = classify_experience(
        posting.title or "", posting.description or "", posting.tags or []
    )
    category = classify_category(posting.title or "", posting.tags or [])
    accessibility = classify_accessibility(posting.url or "", posting.description or "")

    if existing:
        changed = False
        for attr, val in [
            ("title", posting.title),
            ("company", posting.company),
            ("location", posting.location),
            ("remote_type", posting.remote_type or "unknown"),
            ("experience_level", experience_level),
            ("category", category),
            ("accessibility", accessibility),
            ("salary", posting.salary),
            ("description", posting.description),
            ("url", posting.url),
            ("tags", ",".join(posting.tags) if posting.tags else None),
            ("posted_at", posting.posted_at),
        ]:
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        return False, changed

    row = ScrapedJob(
        source=posting.source,
        external_id=posting.external_id,
        title=posting.title,
        company=posting.company,
        location=posting.location,
        remote_type=posting.remote_type or "unknown",
        experience_level=experience_level,
        category=category,
        accessibility=accessibility,
        salary=posting.salary,
        tags=",".join(posting.tags) if posting.tags else None,
        description=posting.description,
        url=posting.url,
        posted_at=posting.posted_at,
        scraped_at=datetime.utcnow(),
    )
    db.session.add(row)
    return True, False


def run_all_scrapers() -> dict:
    summary = {"sources": {}, "total_new": 0, "total_updated": 0, "total_seen": 0}
    for scraper in SCRAPERS:
        postings = scraper.safe_fetch()
        new_count = updated_count = 0
        for p in postings:
            try:
                inserted, updated = _upsert(p)
                new_count += 1 if inserted else 0
                updated_count += 1 if updated else 0
            except Exception:
                logger.exception("upsert failed for %s:%s", p.source, p.external_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("commit failed for source %s", scraper.name)

        summary["sources"][scraper.name] = {
            "seen": len(postings),
            "new": new_count,
            "updated": updated_count,
        }
        summary["total_seen"] += len(postings)
        summary["total_new"] += new_count
        summary["total_updated"] += updated_count

    return summary
