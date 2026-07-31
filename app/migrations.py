"""One-shot lightweight migrations.

SQLAlchemy's `create_all` only adds *tables*, never columns. When we add a new
column to an existing model, we need to teach the running DB about it. This
module runs on every app startup and is idempotent — if the column already
exists, it's a no-op. If a new column was just added, existing rows get
backfilled using the classifier.
"""
import logging
from sqlalchemy import inspect, text

from .classifier import classify_category, classify_experience
from .database import db

logger = logging.getLogger(__name__)


def _ensure_column(table: str, name: str, ddl: str) -> bool:
    """Add column if missing. Returns True if it was added, False if already there."""
    inspector = inspect(db.engine)
    cols = {c["name"] for c in inspector.get_columns(table)}
    if name in cols:
        return False
    logger.info("migration: adding %s.%s", table, name)
    with db.engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_{name} ON {table} ({name})"
        ))
    return True


def _backfill_experience_and_category() -> None:
    from .models import ScrapedJob
    rows = ScrapedJob.query.filter(
        (ScrapedJob.experience_level == "unknown") | (ScrapedJob.category == "other")
    ).all()
    if not rows:
        return
    logger.info("migration: backfilling experience/category for %d rows", len(rows))
    updated = 0
    for row in rows:
        tags = (row.tags or "").split(",") if row.tags else []
        new_exp = classify_experience(row.title or "", row.description or "", tags)
        new_cat = classify_category(row.title or "", tags)
        changed = False
        if row.experience_level != new_exp:
            row.experience_level = new_exp
            changed = True
        if row.category != new_cat:
            row.category = new_cat
            changed = True
        if changed:
            updated += 1
    if updated:
        try:
            db.session.commit()
            logger.info("migration: backfilled %d rows", updated)
        except Exception:
            db.session.rollback()
            logger.exception("backfill commit failed")


def run_migrations() -> None:
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "scraped_jobs" not in tables:
        return

    added_remote = _ensure_column(
        "scraped_jobs", "remote_type",
        "VARCHAR(16) NOT NULL DEFAULT 'unknown'",
    )
    added_exp = _ensure_column(
        "scraped_jobs", "experience_level",
        "VARCHAR(16) NOT NULL DEFAULT 'unknown'",
    )
    added_cat = _ensure_column(
        "scraped_jobs", "category",
        "VARCHAR(16) NOT NULL DEFAULT 'other'",
    )

    if added_exp or added_cat:
        _backfill_experience_and_category()
    _ = added_remote  # kept for readability; no backfill needed for remote_type
