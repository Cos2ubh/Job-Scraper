"""One-shot lightweight migrations.

SQLAlchemy's `create_all` only adds *tables*, never columns. When we add a new
column to an existing model, we need to teach the running DB about it. This
module runs on every app startup and is idempotent — if the column already
exists, it's a no-op.
"""
import logging
from sqlalchemy import inspect, text

from .database import db

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "scraped_jobs" in tables:
        cols = {c["name"] for c in inspector.get_columns("scraped_jobs")}
        if "remote_type" not in cols:
            logger.info("migration: adding scraped_jobs.remote_type")
            with db.engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE scraped_jobs ADD COLUMN remote_type VARCHAR(16) "
                    "NOT NULL DEFAULT 'unknown'"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_scraped_jobs_remote_type "
                    "ON scraped_jobs (remote_type)"
                ))
