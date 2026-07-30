import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ..database import db
from ..matching import build_scorer, job_text
from ..models import VALID_REMOTE_TYPES, Profile, ScrapedJob
from ..scrapers import run_all_scrapers

logger = logging.getLogger(__name__)

jobs_api_bp = Blueprint("jobs_api", __name__)


@jobs_api_bp.route("/scrape", methods=["POST"])
def trigger_scrape():
    try:
        summary = run_all_scrapers()
        return jsonify({"ok": True, "summary": summary})
    except Exception as exc:
        logger.exception("scrape failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@jobs_api_bp.route("/jobs", methods=["GET"])
def list_jobs():
    q = (request.args.get("q") or "").strip()
    company = (request.args.get("company") or "").strip()
    days = request.args.get("days", type=int)
    remote_type = (request.args.get("remote_type") or "").strip().lower()
    limit = min(request.args.get("limit", default=100, type=int), 500)
    offset = max(request.args.get("offset", default=0, type=int), 0)

    query = ScrapedJob.query

    if q:
        needle = f"%{q}%"
        query = query.filter(
            or_(
                ScrapedJob.title.ilike(needle),
                ScrapedJob.description.ilike(needle),
                ScrapedJob.tags.ilike(needle),
            )
        )
    if company:
        query = query.filter(ScrapedJob.company.ilike(f"%{company}%"))
    if days and days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(
            or_(ScrapedJob.posted_at >= cutoff, ScrapedJob.scraped_at >= cutoff)
        )
    if remote_type in VALID_REMOTE_TYPES and remote_type != "unknown":
        query = query.filter(ScrapedJob.remote_type == remote_type)

    total = query.count()
    jobs = (
        query.order_by(
            ScrapedJob.posted_at.is_(None),
            ScrapedJob.posted_at.desc(),
            ScrapedJob.scraped_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    profile = db.session.get(Profile, 1)
    if profile and (profile.resume_text or profile.keywords):
        scorer = build_scorer(profile.resume_text or "", profile.keywords or "")
        scorer.prime(job_text(j) for j in jobs)
        result = [j.to_dict(match_score=scorer.score(job_text(j))) for j in jobs]
    else:
        result = [j.to_dict() for j in jobs]

    return jsonify({"total": total, "count": len(result), "jobs": result})
