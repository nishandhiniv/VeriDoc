import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # NFR-06: secrets come from the environment. A random key is generated when
    # none is set, which is safe but logs everyone out on restart.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DATA_DIR / 'veridoc.sqlite'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = DATA_DIR / "uploads"
    # Hard cap enforced by Flask itself; the configurable cap is checked in the form.
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    SEED_DEMO = os.environ.get("SEED_DEMO", "1") == "1"
    # Seed in the background so the server answers immediately on slow hosts.
    SEED_DEMO_ASYNC = os.environ.get("SEED_DEMO_ASYNC", "1") == "1"
    SEED_EVALUATION = os.environ.get("SEED_EVALUATION", "1") == "1"
    # Data prepared at image build time (app/prebuild.py), copied in on a fresh disk.
    PREBUILT_DATA_DIR = Path(os.environ["PREBUILT_DATA_DIR"]) if os.environ.get("PREBUILT_DATA_DIR") else None


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SEED_DEMO = False
    SEED_DEMO_ASYNC = False
    SEED_EVALUATION = False
    PREBUILT_DATA_DIR = None
