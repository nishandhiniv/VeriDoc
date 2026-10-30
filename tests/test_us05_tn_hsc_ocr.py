"""US-05 Read the TN HSC mark sheet (FR-V01–V04)."""
import io
import json
import random

import pytest

from dataset.generator import generate, make_student, render_marksheet
from engine import marksheet as ms
from engine.templates_registry import TEMPLATE_DIR, get_template

TN = get_template("tn_hsc")


@pytest.fixture(scope="session")
def samples(tmp_path_factory):
    out = tmp_path_factory.mktemp("dataset")
    truth = generate(out, sheets_per_template=5, clean_per_template=5, photos=False)
    return out, truth


def png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_ac1_all_subjects_with_total_mark_and_confidence(samples):
    out, truth = samples
    rec = next(r for r in truth["marksheets"] if r["template"] == "tn_hsc")
    reading = ms.read_marksheet((out / rec["file"]).read_bytes(), TN)
    assert reading.layout_ok
    assert set(reading.marks) == set(rec["sheet_marks"])
    for subject, mark in rec["sheet_marks"].items():
        assert reading.marks[subject].value == mark
        assert 0 <= reading.marks[subject].confidence <= 100


def test_ac2_fuzzy_alias_maths_maps_to_mathematics():
    student = make_student(TN, random.Random(5), 0)
    student["subjects"] = [s for s in student["subjects"] if s["subject"] != "Mathematics"]
    student["subjects"].append({"subject": "MATHS", "total": 77})
    reading = ms.read_marksheet(png_bytes(render_marksheet(TN, student)), TN)
    assert reading.marks["Mathematics"].value == 77


def test_ac3_preprocessing_binarises_and_scales():
    student = make_student(TN, random.Random(1), 0)
    gray = ms.load_image(png_bytes(render_marksheet(TN, student)))
    out = ms.preprocess(gray)
    assert out.shape[1] >= ms.TARGET_WIDTH
    assert set(out.flatten().tolist()) <= {0, 255}


def test_ac3_marks_are_reread_digits_only_and_disagreement_is_untrusted(monkeypatch):
    student = make_student(TN, random.Random(2), 0)
    data = png_bytes(render_marksheet(TN, student))
    calls = []

    def fake_digits(img, word, pad=12):
        calls.append(word["text"])
        return "1", 99.0  # a second reading that never agrees

    monkeypatch.setattr(ms, "read_digits", fake_digits)
    reading = ms.read_marksheet(data, TN)
    assert calls, "digit-only second reading must run for every mark"
    for mark in reading.marks.values():
        assert mark.confidence == 0.0
        assert "disagree" in mark.note


def test_ac4_template_is_config_not_code():
    config = json.loads((TEMPLATE_DIR / "tn_hsc.json").read_text())
    assert config["mark_column"] == "MARKS OBTAINED"
    assert any(s["name"] == "Mathematics" and "MATHS" in s["aliases"] for s in config["subjects"])


def test_ac5_first_five_clean_sheets_exact(samples):
    out, truth = samples
    recs = [r for r in truth["marksheets"] if r["template"] == "tn_hsc"][:5]
    assert len(recs) == 5
    for rec in recs:
        reading = ms.read_marksheet((out / rec["file"]).read_bytes(), TN)
        got = {s: m.value for s, m in reading.marks.items()}
        assert got == rec["sheet_marks"], rec["file"]


def test_wrong_board_sheet_is_not_recognised():
    cbse = get_template("cbse_xii")
    student = make_student(cbse, random.Random(3), 0)
    reading = ms.read_marksheet(png_bytes(render_marksheet(cbse, student)), TN)
    assert not reading.layout_ok
    assert "doesn't look like" in reading.reason


def test_blank_page_is_not_recognised():
    from PIL import Image
    reading = ms.read_marksheet(png_bytes(Image.new("RGB", (1240, 1754), "white")), TN)
    assert not reading.layout_ok
