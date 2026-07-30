from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@pages_bp.route("/kanban")
def kanban():
    return render_template("kanban.html", active="kanban")


@pages_bp.route("/profile")
def profile():
    return render_template("profile.html", active="profile")


@pages_bp.route("/analytics")
def analytics():
    return render_template("analytics.html", active="analytics")
