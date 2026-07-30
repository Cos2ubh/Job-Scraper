import logging
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, NotFound

from ..database import db
from ..models import VALID_STATUSES, ScrapedJob, TrackedJob

logger = logging.getLogger(__name__)

tracker_api_bp = Blueprint("tracker_api", __name__)


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError as exc:
        raise BadRequest(f"date_applied must be YYYY-MM-DD: {exc}")


@tracker_api_bp.route("/tracker", methods=["GET"])
def list_tracked():
    jobs = TrackedJob.query.order_by(TrackedJob.updated_at.desc()).all()
    return jsonify({"count": len(jobs), "jobs": [j.to_dict() for j in jobs]})


@tracker_api_bp.route("/tracker", methods=["POST"])
def create_tracked():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    company = (data.get("company") or "").strip()
    if not title or not company:
        raise BadRequest("title and company are required")

    status = (data.get("status") or "to_apply").strip()
    if status not in VALID_STATUSES:
        raise BadRequest(f"status must be one of {VALID_STATUSES}")

    job = TrackedJob(
        title=title,
        company=company,
        salary=(data.get("salary") or None),
        url=(data.get("url") or None),
        notes=(data.get("notes") or None),
        status=status,
        date_applied=_parse_date(data.get("date_applied")),
    )
    db.session.add(job)
    db.session.commit()
    return jsonify(job.to_dict()), 201


@tracker_api_bp.route("/tracker/from-scraped/<int:scraped_id>", methods=["POST"])
def clone_from_scraped(scraped_id: int):
    scraped = db.session.get(ScrapedJob, scraped_id)
    if not scraped:
        raise NotFound("scraped job not found")

    existing = TrackedJob.query.filter_by(
        scraped_job_id=scraped_id
    ).first()
    if existing:
        return jsonify({"already_tracked": True, "job": existing.to_dict()}), 200

    job = TrackedJob(
        title=scraped.title,
        company=scraped.company,
        salary=scraped.salary,
        url=scraped.url,
        notes=f"Auto-added from {scraped.source}",
        status="to_apply",
        scraped_job_id=scraped.id,
    )
    db.session.add(job)
    db.session.commit()
    return jsonify(job.to_dict()), 201


@tracker_api_bp.route("/tracker/<int:job_id>", methods=["PATCH"])
def update_tracked(job_id: int):
    job = db.session.get(TrackedJob, job_id)
    if not job:
        raise NotFound("tracked job not found")

    data = request.get_json(silent=True) or {}

    if "status" in data:
        status = (data["status"] or "").strip()
        if status not in VALID_STATUSES:
            raise BadRequest(f"status must be one of {VALID_STATUSES}")
        job.status = status
        if status == "applied" and not job.date_applied:
            job.date_applied = date.today()

    for field in ("title", "company", "salary", "url", "notes"):
        if field in data:
            val = data[field]
            setattr(job, field, val.strip() if isinstance(val, str) and val.strip() else (val or None))

    if "date_applied" in data:
        job.date_applied = _parse_date(data.get("date_applied"))

    db.session.commit()
    return jsonify(job.to_dict())


@tracker_api_bp.route("/tracker/<int:job_id>", methods=["DELETE"])
def delete_tracked(job_id: int):
    job = db.session.get(TrackedJob, job_id)
    if not job:
        raise NotFound("tracked job not found")
    db.session.delete(job)
    db.session.commit()
    return jsonify({"ok": True, "deleted_id": job_id})
