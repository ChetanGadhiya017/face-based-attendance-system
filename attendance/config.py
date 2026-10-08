"""Configuration from environment variables (see .env.example)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'attendance.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    MODELS_DIR = os.getenv("MODELS_DIR", str(BASE_DIR / "instance" / "models"))
    # Cosine similarity threshold for SFace. OpenCV suggests 0.363; a slightly stricter
    # value plus a margin over the runner-up avoids confusing classmates.
    RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.42"))
    RECOGNITION_MARGIN = float(os.getenv("RECOGNITION_MARGIN", "0.05"))
    LATE_AFTER_MINUTES = int(os.getenv("LATE_AFTER_MINUTES", "10"))
    MIN_ATTENDANCE_PERCENT = int(os.getenv("MIN_ATTENDANCE_PERCENT", "75"))
    MAX_FACE_SAMPLES = 8

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # webcam frames and photos
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
