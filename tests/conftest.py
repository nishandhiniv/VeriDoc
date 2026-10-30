import pytest

from app import create_app
from app.config import TestConfig


def make_config(tmp_path, **extra):
    attrs = {
        "DATA_DIR": tmp_path,
        "UPLOAD_DIR": tmp_path / "uploads",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite'}",
        **extra,
    }
    return type("Cfg", (TestConfig,), attrs)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_REVIEWER_PASSWORD", "reviewer-pass-123")
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "admin-pass-123")
    app = create_app(make_config(tmp_path))
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
