from flask import Blueprint, jsonify, request

from ..database import db
from ..models import Profile

profile_api_bp = Blueprint("profile_api", __name__)


def _get_or_create_profile() -> Profile:
    profile = db.session.get(Profile, 1)
    if not profile:
        profile = Profile(id=1, resume_text="", keywords="")
        db.session.add(profile)
        db.session.commit()
    return profile


@profile_api_bp.route("/profile", methods=["GET"])
def get_profile():
    return jsonify(_get_or_create_profile().to_dict())


@profile_api_bp.route("/profile", methods=["PUT"])
def put_profile():
    data = request.get_json(silent=True) or {}
    profile = _get_or_create_profile()
    if "resume_text" in data:
        profile.resume_text = (data.get("resume_text") or "").strip()
    if "keywords" in data:
        profile.keywords = (data.get("keywords") or "").strip()
    db.session.commit()
    return jsonify(profile.to_dict())
