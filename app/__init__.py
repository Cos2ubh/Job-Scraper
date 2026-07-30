import logging
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
