"""US-09 login & roles, US-08 validation report, US-10 queue & decisions."""
import re

import pytest

from app import create_app
from app.models import Application, Decision, User
from tests.conftest import make_config
from tests.helpers import login, sample_photo, sample_sheet, submit_application


@pytest.fixture
def two_apps(app, client):
    """One clean application (auto-cleared) and one with a planted mismatch (needs review)."""
    sheet, marks, _ = sample_sheet(seed=7)
    submit_application(client, marks, sheet, sample_photo())
    bad = dict(marks)
    subject = next(iter(bad))
    bad[subject] = (bad[subject] + 9) % 101
    sheet2, marks2, _ = sample_sheet(seed=8)
    bad2 = dict(marks2)
    s2 = next(iter(bad2))
    bad2[s2] = (bad2[s2] + 9) % 101
    submit_application(client, bad2, sheet2, sample_photo())
    with app.app_context():
        apps = Application.query.order_by(Application.id).all()
        return {"clean": apps[0].reference, "bad": apps[1].reference, "bad_subject": s2,
                "bad_entered": bad2[s2], "bad_uploaded": marks2[s2],
                "statuses": [a.auto_status for a in apps]}


# ---------------------------------------------------------------- US-09

def test_us09_ac1_correct_login(client):
    resp = login(client)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/staff/")


@pytest.mark.parametrize("email,password", [("reviewer@veridoc.test", "wrong"), ("nobody@veridoc.test", "reviewer-pass-123")])
def test_us09_ac1_wrong_login_same_message(client, email, password):
    resp = client.post("/staff/login", data={"email": email, "password": password})
    assert resp.status_code == 401
    assert b"Email or password is incorrect." in resp.data


def test_us09_ac2_passwords_hashed(app):
    with app.app_context():
        for u in User.query.all():
            assert u.password_hash.startswith(("scrypt:", "pbkdf2:"))


def test_us09_ac3_reviewer_gets_403_on_accuracy_admin_allowed(app):
    c1 = app.test_client()
    login(c1, "reviewer")
    assert c1.get("/staff/").status_code == 200
    assert c1.get("/staff/accuracy").status_code == 403
    c2 = app.test_client()
    login(c2, "admin")
    assert c2.get("/staff/accuracy").status_code == 200


def test_us09_ac4_csrf_required(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_REVIEWER_PASSWORD", "reviewer-pass-123")
    app = create_app(make_config(tmp_path, WTF_CSRF_ENABLED=True))
    client = app.test_client()
    resp = client.post("/staff/login", data={"email": "reviewer@veridoc.test", "password": "reviewer-pass-123"})
    assert resp.status_code == 400  # rejected: no CSRF token
    page = client.get("/staff/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    resp = client.post("/staff/login", data={"email": "reviewer@veridoc.test", "password": "reviewer-pass-123",
                                             "csrf_token": token})
    assert resp.status_code == 302


def test_us09_ac5_logout_ends_session_and_no_cache(client):
    login(client)
    assert client.get("/staff/").headers["Cache-Control"] == "no-store"
    client.post("/staff/logout")
    resp = client.get("/staff/")
    assert resp.status_code == 302 and "/staff/login" in resp.headers["Location"]


def test_us09_open_redirect_blocked(client):
    resp = client.post("/staff/login?next=https://evil.example/", data={
        "email": "reviewer@veridoc.test", "password": "reviewer-pass-123"})
    assert resp.headers["Location"].endswith("/staff/")


# ---------------------------------------------------------------- US-08

def test_us08_ac1_catalogue_format_table_and_status(client, two_apps):
    login(client)
    html = client.get(f"/staff/applications/{two_apps['bad']}").get_data(as_text=True)
    assert "<th scope=\"col\">Validation</th><th scope=\"col\">Result</th><th scope=\"col\">Details</th>" in html
    assert f"{two_apps['bad_subject']} marks" in html
    assert f"Entered: {two_apps['bad_entered']}, Uploaded: {two_apps['bad_uploaded']}" in html
    assert "Needs review" in html


def test_us08_ac2_rows_show_rule_and_confidence(client, two_apps):
    login(client)
    html = client.get(f"/staff/applications/{two_apps['clean']}").get_data(as_text=True)
    assert "Rule: exact match · OCR confidence" in html
    assert "Rule: minimum 300 × 400 px" in html


def test_us08_ac3_documents_shown(client, two_apps):
    login(client)
    ref = two_apps["clean"]
    html = client.get(f"/staff/applications/{ref}").get_data(as_text=True)
    assert f"/staff/applications/{ref}/file/marksheet" in html and f"/staff/applications/{ref}/file/photo" in html
    resp = client.get(f"/staff/applications/{ref}/file/photo")
    assert resp.status_code == 200 and resp.mimetype.startswith("image/")


def test_us08_ac4_icon_and_text_not_colour_only(client, two_apps):
    login(client)
    html = client.get(f"/staff/applications/{two_apps['bad']}").get_data(as_text=True)
    assert 'data-icon="✕">Mismatch</span>' in html
    assert 'data-icon="✓">Match</span>' in html


def test_us08_ac5_reopening_report_does_not_rerun_ocr(client, two_apps, monkeypatch):
    import engine.validate
    login(client)
    monkeypatch.setattr(engine.validate, "read_marksheet",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("OCR re-run")))
    assert client.get(f"/staff/applications/{two_apps['bad']}").status_code == 200


def test_us08_ac6_report_and_files_require_login(client, two_apps):
    for url in [f"/staff/applications/{two_apps['bad']}", f"/staff/applications/{two_apps['bad']}/file/marksheet"]:
        resp = client.get(url)
        assert resp.status_code == 302 and "/staff/login" in resp.headers["Location"]


# ---------------------------------------------------------------- US-10

def test_us10_ac1_queue_columns(client, two_apps):
    login(client)
    html = client.get("/staff/").get_data(as_text=True)
    for col in ["Reference", "Name", "Board", "Submitted", "Status", "Issues"]:
        assert f">{col}</th>" in html
    assert two_apps["bad"] in html and "TN HSC" in html


def test_us10_ac2_default_needs_review_and_filters(client, two_apps):
    assert two_apps["statuses"] == ["auto_cleared", "needs_review"]
    login(client)
    default = client.get("/staff/").get_data(as_text=True)
    assert two_apps["bad"] in default and two_apps["clean"] not in default
    cleared = client.get("/staff/?status=auto_cleared").get_data(as_text=True)
    assert two_apps["clean"] in cleared and two_apps["bad"] not in cleared


def test_us10_ac3_reject_and_reupload_require_comment(client, two_apps):
    login(client)
    for decision in ("reject", "reupload"):
        resp = client.post(f"/staff/applications/{two_apps['bad']}/decision", data={"decision": decision, "comment": " "})
        assert resp.status_code == 400
        assert b"Add a comment" in resp.data
    resp = client.post(f"/staff/applications/{two_apps['bad']}/decision", data={"decision": "nonsense"})
    assert resp.status_code == 400


def test_us10_ac4_decided_case_moves_to_decided_with_audit(app, client, two_apps):
    login(client)
    resp = client.post(f"/staff/applications/{two_apps['bad']}/decision",
                       data={"decision": "reupload", "comment": "Please upload a clearer mark sheet."})
    assert resp.status_code == 302
    first = client.get("/staff/").get_data(as_text=True)
    assert "Re-upload requested." in first  # confirmation message
    table = first.split('id="queue"')[1] if 'id="queue"' in first else ""
    assert two_apps["bad"] not in table
    decided = client.get("/staff/?status=decided").get_data(as_text=True)
    assert two_apps["bad"] in decided and "Re-upload requested" in decided
    report = client.get(f"/staff/applications/{two_apps['bad']}").get_data(as_text=True)
    assert "Demo Reviewer" in report and "Please upload a clearer mark sheet." in report


def test_us10_ac5_decisions_never_overwritten(app, client, two_apps):
    login(client)
    url = f"/staff/applications/{two_apps['bad']}/decision"
    client.post(url, data={"decision": "reject", "comment": "Marks don't match."})
    client.post(url, data={"decision": "approve", "comment": ""})
    with app.app_context():
        a = Application.query.filter_by(reference=two_apps["bad"]).one()
        history = Decision.query.filter_by(application_id=a.id).order_by(Decision.id).all()
        assert [d.decision for d in history] == ["reject", "approve"]
        assert all(d.reviewer.email == "reviewer@veridoc.test" and d.created_at for d in history)
        assert a.decision == "approve"


def test_queue_requires_login(client):
    assert client.get("/staff/").status_code == 302
