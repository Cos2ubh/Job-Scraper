import logging
import os
import time
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import Config
from .database import db


def create_app(config_class: type = Config) -> Flask:
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
    )
    app.config.from_object(config_class)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db.init_app(app)

    # Cache-bust static assets so browsers pick up new JS/CSS after a redeploy.
    # In debug mode we use the current time; in prod we'd use a build hash.
    app.config["ASSET_VERSION"] = str(int(time.time())) if app.debug else os.environ.get("ASSET_VERSION", "1")

    @app.context_processor
    def inject_asset_version():
        return {"asset_version": app.config["ASSET_VERSION"]}

    # Force browsers to treat static files as revalidatable each request.
    @app.after_request
    def _cache_headers(resp):
        if resp.mimetype in ("application/javascript", "text/css"):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        return resp

    from .routes.pages import pages_bp
    from .routes.jobs_api import jobs_api_bp
    from .routes.tracker_api import tracker_api_bp
    from .routes.profile_api import profile_api_bp
    from .routes.analytics_api import analytics_api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(jobs_api_bp, url_prefix="/api")
    app.register_blueprint(tracker_api_bp, url_prefix="/api")
    app.register_blueprint(profile_api_bp, url_prefix="/api")
    app.register_blueprint(analytics_api_bp, url_prefix="/api")

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        response = jsonify({"error": err.name, "message": err.description})
        response.status_code = err.code or 500
        return response

    @app.errorhandler(Exception)
    def handle_uncaught(err: Exception):
        app.logger.exception("Unhandled exception")
        return jsonify({"error": "InternalServerError", "message": str(err)}), 500

    return app
