from datetime import datetime, date
from sqlalchemy import UniqueConstraint

from .database import db


VALID_STATUSES = ("to_apply", "applied", "interviewing", "offer", "rejected")
VALID_REMOTE_TYPES = ("remote", "onsite", "hybrid", "unknown")
VALID_EXPERIENCE_LEVELS = ("fresher", "mid", "senior", "unknown")
VALID_CATEGORIES = ("technical", "design", "product", "business", "other")


class ScrapedJob(db.Model):
    __tablename__ = "scraped_jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(32), nullable=False, index=True)
    external_id = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    company = db.Column(db.String(255), nullable=False, default="Unknown")
    location = db.Column(db.String(255))
    remote_type = db.Column(db.String(16), nullable=False, default="unknown", index=True)
    experience_level = db.Column(db.String(16), nullable=False, default="unknown", index=True)
    category = db.Column(db.String(16), nullable=False, default="other", index=True)
    salary = db.Column(db.String(255))
    tags = db.Column(db.String(500))
    description = db.Column(db.Text)
    url = db.Column(db.String(1000), nullable=False)
    posted_at = db.Column(db.DateTime, index=True)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self, match_score: float | None = None) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "remote_type": self.remote_type or "unknown",
            "experience_level": self.experience_level or "unknown",
            "category": self.category or "other",
            "salary": self.salary,
            "tags": [t for t in (self.tags or "").split(",") if t],
            "description": self.description,
            "url": self.url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "match_score": round(match_score, 1) if match_score is not None else None,
        }


class TrackedJob(db.Model):
    __tablename__ = "tracked_jobs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    salary = db.Column(db.String(255))
    url = db.Column(db.String(1000))
    notes = db.Column(db.Text)
    status = db.Column(db.String(32), nullable=False, default="to_apply", index=True)
    date_applied = db.Column(db.Date)
    scraped_job_id = db.Column(db.Integer, db.ForeignKey("scraped_jobs.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "salary": self.salary,
            "url": self.url,
            "notes": self.notes,
            "status": self.status,
            "date_applied": self.date_applied.isoformat() if self.date_applied else None,
            "scraped_job_id": self.scraped_job_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Profile(db.Model):
    __tablename__ = "profile"

    id = db.Column(db.Integer, primary_key=True)
    resume_text = db.Column(db.Text, default="")
    keywords = db.Column(db.Text, default="")
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "resume_text": self.resume_text or "",
            "keywords": self.keywords or "",
            "updated_at": self.updated_at.isoformat(),
        }
