"""Startup seeding (FR-S04): demo accounts and default settings.

Render's free plan resets the disk, so this runs on every start and only
inserts what is missing (US-13 AC2).
"""
import logging
import os
import secrets

from .models import User, db
from .settings_store import ensure_default_settings

log = logging.getLogger(__name__)

DEMO_ACCOUNTS = [
    ("reviewer", "Demo Reviewer", "DEMO_REVIEWER_EMAIL", "reviewer@veridoc.test", "DEMO_REVIEWER_PASSWORD"),
    ("admin", "Demo Admin", "DEMO_ADMIN_EMAIL", "admin@veridoc.test", "DEMO_ADMIN_PASSWORD"),
]


def seed_accounts():
    for role, name, email_var, default_email, password_var in DEMO_ACCOUNTS:
        email = os.environ.get(email_var, default_email).strip().lower()
        if User.query.filter_by(email=email).first():
            continue
        password = os.environ.get(password_var)
        if not password:
            # No password configured: generate one rather than ship a known default (NFR-06).
            password = secrets.token_urlsafe(12)
            log.warning("%s not set. Generated password for %s: %s", password_var, email, password)
        user = User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
    db.session.commit()


def seed_all(app):
    ensure_default_settings()
    seed_accounts()
    if app.config.get("SEED_DEMO"):
        from .demo import start_demo_seeding

        start_demo_seeding(app)
