"""US-13 Foundation: database, settings, seed data, error pages."""
from pathlib import Path

from flask import abort
from sqlalchemy import inspect

from app import create_app
from app.models import Setting, User, db
from engine.settings import DEFAULT_SETTINGS
from tests.conftest import make_config

ROOT = Path(__file__).resolve().parent.parent


def test_ac1_tables_created_and_accounts_and_settings_seeded(app):
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
        assert {"users", "applications", "entered_marks", "check_results",
                "decisions", "settings", "evaluation_runs"} <= tables
        roles = sorted(u.role for u in User.query.all())
        assert roles == ["admin", "reviewer"]
        stored = {s.key: s.value for s in Setting.query.all()}
        assert stored == DEFAULT_SETTINGS


def test_ac2_restart_does_not_duplicate_seed_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "x-admin")
    cfg = make_config(tmp_path)
    create_app(cfg)
    app2 = create_app(cfg)
    with app2.app_context():
        assert User.query.count() == 2
        assert Setting.query.count() == len(DEFAULT_SETTINGS)


def test_ac2_restart_keeps_changed_settings(tmp_path):
    cfg = make_config(tmp_path)
    app1 = create_app(cfg)
    with app1.app_context():
        from app.settings_store import save_setting
        save_setting("photo_min_width", 350)
    app2 = create_app(cfg)
    with app2.app_context():
        from app.settings_store import load_settings
        assert load_settings()["photo_min_width"] == 350


def test_ac3_friendly_404(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert b"Page not found" in resp.data
    assert b"Go to the home page" in resp.data


def _app_with_error_routes(tmp_path):
    app = create_app(make_config(tmp_path, PROPAGATE_EXCEPTIONS=False))

    @app.route("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    @app.route("/forbidden")
    def forbidden():
        abort(403)

    return app


def test_ac3_500_never_shows_stack_trace(tmp_path):
    client = _app_with_error_routes(tmp_path).test_client()
    resp = client.get("/boom")
    assert resp.status_code == 500
    assert b"Something went wrong" in resp.data
    assert b"Traceback" not in resp.data
    assert b"secret internal detail" not in resp.data


def test_ac3_friendly_403(tmp_path):
    client = _app_with_error_routes(tmp_path).test_client()
    resp = client.get("/forbidden")
    assert resp.status_code == 403
    assert b"have access" in resp.data


def test_ac4_passwords_from_env_and_hashed(app):
    with app.app_context():
        admin = User.query.filter_by(role="admin").one()
        assert admin.check_password("admin-pass-123")
        assert "admin-pass-123" not in admin.password_hash


def test_ac4_missing_password_env_generates_random_not_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_REVIEWER_PASSWORD", raising=False)
    app = create_app(make_config(tmp_path))
    with app.app_context():
        for user in User.query.all():
            for guess in ("", "admin", "password", "change-me", "reviewer"):
                assert not user.check_password(guess)


def test_ac4_no_secrets_committed():
    ignored = (ROOT / ".gitignore").read_text()
    assert ".env" in ignored.split()
    assert "data/" in ignored.split()
    example = (ROOT / ".env.example").read_text()
    assert "change-me" in example  # placeholders only


def test_security_headers(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_ac1_demo_applications_seeded_through_real_engine_once(tmp_path, monkeypatch):
    from app.models import Application
    cfg = make_config(tmp_path, SEED_DEMO=True, SEED_DEMO_ASYNC=False)
    app = create_app(cfg)
    with app.app_context():
        demo = Application.query.filter_by(is_demo=True).all()
        statuses = {a.auto_status for a in demo}
        assert len(demo) >= 6
        assert statuses == {"auto_cleared", "needs_review"}  # a realistic mix
        assert all(a.checks for a in demo)  # every one went through validation
    create_app(cfg)  # restart
    with app.app_context():
        assert Application.query.filter_by(is_demo=True).count() == len(demo)


def test_startup_evaluation_is_not_retried_after_an_interrupted_attempt(tmp_path, monkeypatch):
    """Regression: an out-of-memory kill during the startup run caused an endless restart loop."""
    from app import evaluation_runner
    from app.models import EvaluationRun, db
    calls = []
    monkeypatch.setattr(evaluation_runner, "_execute", lambda app, run_id: calls.append(run_id))
    cfg = make_config(tmp_path, SEED_DEMO=True, SEED_DEMO_ASYNC=False, SEED_EVALUATION=True)
    monkeypatch.setattr("app.demo.seed_demo_applications", lambda app: None)
    create_app(cfg)            # first boot: one startup run (left 'running', as if killed)
    create_app(cfg)            # restart: interrupted run marked failed, NOT retried
    app = create_app(cfg)
    with app.app_context():
        assert len(calls) == 1
        assert [r.status for r in EvaluationRun.query.all()] == ["failed"]


def test_prebuilt_data_is_copied_on_fresh_disk_without_accounts(tmp_path, monkeypatch):
    from app import prebuild
    from app.models import Application, EvaluationRun
    from app.evaluation_runner import _execute
    monkeypatch.setattr("app.demo.DEMO_CASES", [("tn_hsc", 101, "correct", (600, 800))])
    monkeypatch.setattr("evaluation.evaluate.evaluate_marksheets",
                        lambda d, s, e: {"sheets": 0, "groups": [], "outcomes": {"false_match": 0}})
    monkeypatch.setattr("evaluation.evaluate.evaluate_photos", lambda d, s, e: {"photos": 0})
    monkeypatch.setattr("app.evaluation_runner.generate", lambda target: (target.mkdir(parents=True, exist_ok=True),
                        (target / "ground_truth.json").write_text('{"seed": 1}')))
    prebuild.main(tmp_path / "seed")
    live = tmp_path / "live"
    app = create_app(make_config(live, PREBUILT_DATA_DIR=tmp_path / "seed", SEED_DEMO=True,
                                 SEED_EVALUATION=True, UPLOAD_DIR=live / "uploads"))
    with app.app_context():
        assert Application.query.filter_by(is_demo=True).count() == 1
        assert EvaluationRun.query.filter_by(status="done").count() == 1
        assert sorted(u.role for u in User.query.all()) == ["admin", "reviewer"]
