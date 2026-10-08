"""Face Recognition Attendance: Flask application factory."""

from __future__ import annotations

import os
from datetime import datetime

from flask import Flask, render_template

from .config import Config
from .extensions import csrf, db, login_manager
from .face import FaceEngine

__version__ = "2.0.0"


def create_app(config: type[Config] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config or Config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    app.extensions["face_engine"] = FaceEngine(app.config["MODELS_DIR"])

    from . import models  # noqa: F401 - register tables
    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .cli import register_cli
    from .views import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    register_cli(app)

    @login_manager.user_loader
    def load_user(uid: str):
        return db.session.get(models.User, int(uid))

    @app.context_processor
    def inject():
        return {"app_version": __version__, "now": datetime.now(), "min_percent": app.config["MIN_ATTENDANCE_PERCENT"]}

    @app.template_filter("pct")
    def pct(v):
        return "–" if v is None else f"{v:.0f}%"

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(self)")
        return resp

    for code in (403, 404):
        app.register_error_handler(code, lambda e, c=code: (render_template("error.html", code=c, error=e), c))

    with app.app_context():
        db.create_all()
    return app
