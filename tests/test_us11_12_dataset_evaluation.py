"""US-11 synthetic dataset generator, US-12 evaluation and accuracy page."""
import hashlib
import json

import pytest
from PIL import Image

from app.models import EvaluationRun, db
from dataset.generator import FIRST_NAMES, LAST_NAMES, PHOTO_RULES, generate
from engine.settings import DEFAULT_SETTINGS
from evaluation.evaluate import run_evaluation, to_markdown
from tests.helpers import login


@pytest.fixture(scope="module")
def full(tmp_path_factory):
    out = tmp_path_factory.mktemp("full")
    return out, generate(out)


def digest(folder):
    h = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- US-11

def test_us11_ac1_sizes_and_ground_truth(full):
    out, truth = full
    sheets = truth["marksheets"]
    assert len(sheets) == 40 and len(truth["photos"]) == 30
    for template in ("tn_hsc", "cbse_xii"):
        mine = [s for s in sheets if s["template"] == template]
        assert len(mine) == 20
        assert sum(s["variant"] == "clean" for s in mine) == 10
    assert json.loads((out / "ground_truth.json").read_text()) == truth
    assert all((out / r["file"]).exists() for r in sheets + truth["photos"])


def test_us11_ac2_repeatable(full, tmp_path):
    out, _ = full
    again = tmp_path / "again"
    generate(again)
    assert digest(out) == digest(again)


def test_us11_ac3_degraded_variants_differ(full):
    out, truth = full
    clean = next(r for r in truth["marksheets"] if r["variant"] == "clean")
    deg = next(r for r in truth["marksheets"] if r["variant"] == "degraded")
    assert "angle" in deg and deg["angle"] != 0  # skew
    c = Image.open(out / clean["file"]).convert("L")
    d = Image.open(out / deg["file"]).convert("L")
    from PIL import ImageStat
    assert ImageStat.Stat(d).mean[0] < ImageStat.Stat(c).mean[0] - 30  # low light
    assert deg["file"].endswith(".jpg")  # JPEG artefacts on top of blur and noise
    import numpy as np
    assert np.asarray(d, dtype=float).std() > 0


def test_us11_ac4_planted_errors_recorded(full):
    _, truth = full
    sheets = truth["marksheets"]
    planted = [s for s in sheets if s["planted_error"]]
    assert len(planted) / len(sheets) >= 0.25
    kinds = {s["planted_error"] for s in planted}
    assert {"mismatch", "mismatch2", "missing", "not_entered"} == kinds
    for s in planted:
        assert any(v != "match" for v in s["expected"].values())
    for s in sheets:
        if not s["planted_error"]:
            assert s["entered_marks"] == s["sheet_marks"]


def test_us11_ac5_photo_set_covers_every_rule(full):
    _, truth = full
    for rule in PHOTO_RULES:
        assert any(p["expected"][rule] == "fail" for p in truth["photos"]), rule
    valid = [p for p in truth["photos"] if all(v == "pass" for v in p["expected"].values())]
    assert len(valid) >= 5


def test_us11_ac6_fake_names_no_real_data(full):
    _, truth = full
    for s in truth["marksheets"]:
        first, last = s["student"]["name"].split()
        assert first in FIRST_NAMES and last in LAST_NAMES


# ---------------------------------------------------------------- US-12

@pytest.fixture
def small_dataset(app):
    target = app.config["DATA_DIR"] / "dataset"
    generate(target, sheets_per_template=4, clean_per_template=2)
    return target


def test_us12_ac1_cli_and_button_produce_same_results(app, client, small_dataset):
    login(client, "admin")
    resp = client.post("/staff/accuracy/run")
    assert resp.status_code == 302
    with app.app_context():
        run = EvaluationRun.query.filter_by(status="done").one()
        stored = run.report
    direct = run_evaluation(small_dataset, DEFAULT_SETTINGS)
    for key in ("marks", "photos", "false_match", "errors", "dataset"):
        assert stored[key] == direct[key]


def test_us12_ac1_command_line_module(small_dataset, capsys, monkeypatch):
    import sys
    from evaluation.__main__ import main
    monkeypatch.setattr(sys, "argv", ["evaluation", str(small_dataset)])
    main()
    assert "False matches (fail-safe gate)" in capsys.readouterr().out


def test_us12_ac2_ac3_ac5_page_shows_metrics_errors_and_label(app, client, small_dataset):
    login(client, "admin")
    client.post("/staff/accuracy/run")
    html = client.get("/staff/accuracy").get_data(as_text=True)
    for text in ["Mark extraction accuracy, clean sheets", "degraded sheets", "Planted errors detected (recall)",
                 "precision", "False matches on planted errors", "Photo rule results", "sent to review",
                 "TN HSC", "CBSE XII", "Every error in this run"]:
        assert text in html
    assert "Measured on synthetic data" in html and "n = 8 mark sheets + 30 photos" in html


def test_us12_ac4_red_warning_when_false_match(app, client):
    fake = {"run_at": "2026-10-30 10:00 UTC", "dataset": {"marksheets": 1, "photos": 1, "seed": 1},
            "settings": {}, "false_match": 2, "errors": [], "seconds": 1,
            "marks": {"clean_accuracy": 100, "degraded_accuracy": 100, "wrong_trusted": 0, "groups": [],
                      "outcomes": {"recall": 80, "precision": 100},
                      "applications": {"planted_to_review_pct": 80, "clean_to_review_pct": 0}},
            "photos": {"overall": 100, "rules": []}}
    with app.app_context():
        db.session.add(EvaluationRun(status="done", report_json=json.dumps(fake)))
        db.session.commit()
    login(client, "admin")
    html = client.get("/staff/accuracy").get_data(as_text=True)
    assert "Fail-safe broken: 2 planted errors were reported as Match" in html
    assert "gate--bad" in html


def test_us12_reviewer_cannot_run(client):
    login(client, "reviewer")
    assert client.post("/staff/accuracy/run").status_code == 403


def test_us12_markdown_export(small_dataset):
    text = to_markdown(run_evaluation(small_dataset, DEFAULT_SETTINGS))
    assert text.startswith("# VeriDoc accuracy report") and "Measured on synthetic data" in text
