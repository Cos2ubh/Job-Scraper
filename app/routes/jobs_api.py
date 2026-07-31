import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import case, or_

from ..database import db
from ..matching import build_scorer, job_text
from ..models import (
    VALID_CATEGORIES,
    VALID_EXPERIENCE_LEVELS,
    VALID_REMOTE_TYPES,
    Profile,
    ScrapedJob,
)
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
    experience_level = (request.args.get("experience_level") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    include_paywalled = (request.args.get("include_paywalled") or "0").strip().lower() in {"1", "true", "yes"}
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
    if experience_level in VALID_EXPERIENCE_LEVELS and experience_level != "unknown":
        query = query.filter(ScrapedJob.experience_level == experience_level)
    if category in VALID_CATEGORIES:
        query = query.filter(ScrapedJob.category == category)
    # Compute hidden-paywalled count against the same filter set for the UI hint.
    paywalled_hidden = 0
    if not include_paywalled:
        paywalled_hidden = query.filter(ScrapedJob.accessibility == "paywalled").count()
        query = query.filter(ScrapedJob.accessibility != "paywalled")

    total = query.count()
    # When paywalled jobs are included, push them to the bottom so free ones
    # dominate the top of the ranking.
    paywall_rank = case((ScrapedJob.accessibility == "paywalled", 1), else_=0)
    jobs = (
        query.order_by(
            paywall_rank.asc(),
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

    return jsonify({
        "total": total,
        "count": len(result),
        "paywalled_hidden": paywalled_hidden,
        "jobs": result,
    })
