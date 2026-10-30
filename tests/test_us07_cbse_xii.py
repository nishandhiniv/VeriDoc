"""US-07 Read the CBSE XII mark sheet (FR-V03, FR-V04)."""
import io
import random

import pytest

from dataset.generator import generate, make_student, render_marksheet
from engine import marksheet as ms
from engine import validate as v
from engine.settings import DEFAULT_SETTINGS
from engine.templates_registry import get_template
from tests.helpers import sample_photo

CBSE = get_template("cbse_xii")


def sheet_bytes(student):
    buf = io.BytesIO()
    render_marksheet(CBSE, student).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    out = tmp_path_factory.mktemp("cbse")
    return out, generate(out, sheets_per_template=5, clean_per_template=5, photos=False)


def test_ac1_total_column_extracted(samples):
    out, truth = samples
    rec = next(r for r in truth["marksheets"] if r["template"] == "cbse_xii")
    reading = ms.read_marksheet((out / rec["file"]).read_bytes(), CBSE)
    assert reading.layout_ok
    assert {s: m.value for s, m in reading.marks.items()} == rec["sheet_marks"]


def test_ac2_total_used_not_theory_or_practical():
    student = make_student(CBSE, random.Random(9), 0)
    for s in student["subjects"]:
        assert s["theory"] != s["total"] or s["practical"] == 0
    # Force a clear case: theory 60, practical 25, total 85.
    s = student["subjects"][0]
    s.update(theory=60, practical=25, total=85)
    reading = ms.read_marksheet(sheet_bytes(student), CBSE)
    assert reading.marks[s["subject"]].value == 85


def test_ac3_first_five_clean_sheets_exact(samples):
    out, truth = samples
    recs = [r for r in truth["marksheets"] if r["template"] == "cbse_xii"][:5]
    assert len(recs) == 5
    for rec in recs:
        reading = ms.read_marksheet((out / rec["file"]).read_bytes(), CBSE)
        assert {s: m.value for s, m in reading.marks.items()} == rec["sheet_marks"], rec["file"]


def test_misread_grade_does_not_break_subject_name():
    """Regression: grade "C1" OCR'd as "Cl" used to stop the subject being recognised."""
    words = [{"text": t, "conf": 95.0, "x": x, "y": 0, "w": 40, "h": 20, "line": (1, 1, 1)}
             for t, x in [("042", 100), ("PHYSICS", 190), ("49", 600), ("10", 745), ("059", 905), ("Cl", 1030)]]
    header = [{"text": t, "conf": 95.0, "x": x, "y": -40, "w": 60, "h": 20, "line": (1, 1, 0)}
              for t, x in [("CODE", 100), ("SUBJECT", 190), ("TOTAL", 905)]]
    import numpy as np
    img = np.full((200, 1240), 255, dtype=np.uint8)
    original = ms.read_digits
    try:
        ms.read_digits = lambda img, word, pad=12: (word["text"], 95.0)
        marks = ms.parse_lines([header, words], CBSE, img, (905, 935), header)
    finally:
        ms.read_digits = original
    assert marks["Physics"].value == 59


# ---- AC4: all US-06 fail-safe rules also hold for CBSE XII

ENTERED = {"English Core": 80, "Mathematics": 70, "Physics": 65, "Chemistry": 72, "Biology": 90}


def run_stubbed(monkeypatch, reading=None, error=None):
    def fake(data, template):
        if error:
            raise error
        return reading
    monkeypatch.setattr(v, "read_marksheet", fake)
    return v.validate_application(ENTERED, b"x", sample_photo(), "cbse_xii", DEFAULT_SETTINGS)


def test_ac4_low_confidence_is_unreadable(monkeypatch):
    marks = {s: ms.ReadMark(s, m, 95) for s, m in ENTERED.items()}
    marks["Physics"] = ms.ReadMark("Physics", 65, 30)
    res = run_stubbed(monkeypatch, ms.SheetReading(layout_ok=True, marks=marks))
    assert next(c for c in res.checks if c.name == "Physics").result == "unreadable"
    assert res.status == v.NEEDS_REVIEW


def test_ac4_unknown_layout_is_review(monkeypatch):
    res = run_stubbed(monkeypatch, ms.SheetReading(layout_ok=False, reason="header not found"))
    assert res.status == v.NEEDS_REVIEW
    assert not any(c.result == "match" for c in res.checks)


def test_ac4_processing_error_is_review(monkeypatch):
    res = run_stubbed(monkeypatch, error=RuntimeError("boom"))
    assert res.status == v.NEEDS_REVIEW
    assert any(c.section == "system" and c.result == "error" for c in res.checks)


def test_ac4_real_cbse_mismatch_detected():
    student = make_student(CBSE, random.Random(21), 0)
    entered = {s["subject"]: s["total"] for s in student["subjects"]}
    subject = list(entered)[2]
    entered[subject] = entered[subject] - 5 if entered[subject] >= 5 else entered[subject] + 5
    res = v.validate_application(entered, sheet_bytes(student), sample_photo(), "cbse_xii", DEFAULT_SETTINGS)
    assert next(c for c in res.checks if c.name == subject).result == "mismatch"
    assert res.status == v.NEEDS_REVIEW
