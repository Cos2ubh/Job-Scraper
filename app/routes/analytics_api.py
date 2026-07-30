from collections import Counter, defaultdict
from datetime import date, timedelta

from flask import Blueprint, jsonify
from sqlalchemy import func

from ..database import db
from ..models import VALID_STATUSES, TrackedJob

analytics_api_bp = Blueprint("analytics_api", __name__)


@analytics_api_bp.route("/analytics", methods=["GET"])
def analytics():
    jobs: list[TrackedJob] = TrackedJob.query.all()

    status_counts = Counter({s: 0 for s in VALID_STATUSES})
    for j in jobs:
        if j.status in status_counts:
            status_counts[j.status] += 1

    applied_states = ("applied", "interviewing", "offer", "rejected")
    interview_states = ("interviewing", "offer")
    applied_total = sum(status_counts[s] for s in applied_states)
    interview_total = sum(status_counts[s] for s in interview_states)
    offer_total = status_counts["offer"]

    interview_rate = (interview_total / applied_total * 100.0) if applied_total else 0.0
    offer_rate = (offer_total / applied_total * 100.0) if applied_total else 0.0

    # applications-over-time — last 30 days, bucketed by date_applied (or created_at fallback)
    today = date.today()
    start = today - timedelta(days=29)
    buckets: dict[date, int] = defaultdict(int)
    for j in jobs:
        d = j.date_applied or j.created_at.date()
        if d >= start and d <= today:
            buckets[d] += 1
    timeline = [
        {"date": (start + timedelta(days=i)).isoformat(),
         "count": buckets.get(start + timedelta(days=i), 0)}
        for i in range(30)
    ]

    top_companies = (
        db.session.query(TrackedJob.company, func.count(TrackedJob.id))
        .group_by(TrackedJob.company)
        .order_by(func.count(TrackedJob.id).desc())
        .limit(5)
        .all()
    )

    return jsonify({
        "total_tracked": len(jobs),
        "status_breakdown": dict(status_counts),
        "applied_total": applied_total,
        "interview_total": interview_total,
        "offer_total": offer_total,
        "interview_rate_pct": round(interview_rate, 1),
        "offer_rate_pct": round(offer_rate, 1),
        "timeline_30d": timeline,
        "top_companies": [{"company": c, "count": n} for c, n in top_companies],
    })
