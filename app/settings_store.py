import json

from engine.settings import DEFAULT_SETTINGS, merged

from .models import Setting, db


def load_settings():
    """Current settings: defaults overridden by values stored in the database."""
    stored = {row.key: row.value for row in Setting.query.all()}
    return merged(stored)


def ensure_default_settings():
    """Insert any missing default settings without touching existing values."""
    existing = {key for (key,) in db.session.query(Setting.key).all()}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.session.add(Setting(key=key, value_json=json.dumps(value)))
    db.session.commit()


def save_setting(key, value):
    if key not in DEFAULT_SETTINGS:
        raise KeyError(key)
    row = db.session.get(Setting, key)
    if row is None:
        row = Setting(key=key)
        db.session.add(row)
    row.value_json = json.dumps(value)
    db.session.commit()
