"""US-06 Compare marks and apply the fail-safe rule (FR-V06–V08, V11, R01).

These tests are release gates SM-2 / SM-3. Written before engine/validate.py.
"""
import io

import pytest

from engine import validate as v
from engine.marksheet import ReadMark, SheetReading
from engine.settings import DEFAULT_SETTINGS
from tests.test_us04_photo import portrait

GOOD_PHOTO = portrait()
SHEET = b"\x89PNG fake bytes, reading is stubbed"


def reading(marks, layout_ok=True, reason=""):
    return SheetReading(layout_ok=layout_ok, reason=reason, title_found=True, header_found=True,
                        marks={s: ReadMark(s, val, conf) for s, (val, conf) in marks.items()})


@pytest.fixture
def stub(monkeypatch):
    def install(sheet_reading=None, error=None):
        def fake(data, template):
            if error:
                raise error
            return sheet_reading
        monkeypatch.setattr(v, "read_marksheet", fake)
        monkeypatch.setattr(v, "check_marksheet_file", lambda data, s: [])
    return install


def run(entered, photo=GOOD_PHOTO):
    return v.validate_application(entered, SHEET, photo, "tn_hsc", DEFAULT_SETTINGS)


def row(result, name):
    return next(c for c in result.checks if c.name == name and c.section == "marks")


SIX = {"Tamil": 80, "English": 92, "Mathematics": 85, "Physics": 70, "Chemistry": 66, "Biology": 90}


def test_ac1_equal_marks_with_good_confidence_match(stub):
    stub(reading({s: (m, 95) for s, m in SIX.items()}))
    res = run(SIX)
    assert row(res, "English").result == "match"
    assert row(res, "English").entered == "92" and row(res, "English").uploaded == "92"


def test_ac2_different_marks_are_a_mismatch_showing_both(stub):
    sheet = dict(SIX, Mathematics=88)
    stub(reading({s: (m, 95) for s, m in sheet.items()}))
    r = row(run(SIX), "Mathematics")
    assert r.result == "mismatch"
    assert r.detail == "Entered: 85, Uploaded: 88"


def test_ac3_entered_subject_missing_on_sheet(stub):
    sheet = {s: m for s, m in SIX.items() if s != "Biology"}
    stub(reading({s: (m, 95) for s, m in sheet.items()}))
    assert row(run(SIX), "Biology").result == "missing"


def test_ac4_subject_on_sheet_not_entered(stub):
    stub(reading({s: (m, 95) for s, m in SIX.items()}))
    entered = {s: m for s, m in SIX.items() if s != "Physics"}
    assert row(run(entered), "Physics").result == "not_entered"


def test_ac5_failsafe_low_confidence_is_unreadable_even_when_digits_equal(stub):
    sheet = {s: (m, 95) for s, m in SIX.items()}
    sheet["Chemistry"] = (66, 40)  # same digits as entered, but OCR is unsure
    stub(reading(sheet))
    res = run(SIX)
    assert row(res, "Chemistry").result == "unreadable"
    assert res.status == v.NEEDS_REVIEW


def test_ac5_failsafe_unread_value_is_unreadable(stub):
    sheet = {s: (m, 95) for s, m in SIX.items()}
    sheet["Tamil"] = (None, 0)
    stub(reading(sheet))
    assert row(run(SIX), "Tamil").result == "unreadable"


def test_ac6_failsafe_unknown_layout_sends_whole_section_to_review(stub):
    stub(reading({s: (m, 99) for s, m in SIX.items()}, layout_ok=False, reason="title not found"))
    res = run(SIX)
    assert res.status == v.NEEDS_REVIEW
    assert all(c.result != "match" for c in res.checks if c.section == "marks")
    layout = next(c for c in res.checks if c.name == "Mark sheet layout")
    assert layout.result == "review" and "title not found" in layout.detail


def test_ac7_failsafe_engine_exception_is_processing_error_never_cleared(stub):
    stub(error=RuntimeError("tesseract crashed"))
    res = run(SIX)
    assert res.status == v.NEEDS_REVIEW
    err = next(c for c in res.checks if c.section == "system")
    assert err.result == "error" and "Processing error" in err.name
    assert all(c.result != "match" for c in res.checks if c.section == "marks")


def test_ac8_completeness_pass_only_when_sets_equal(stub):
    stub(reading({s: (m, 95) for s, m in SIX.items()}))
    ok = run(SIX)
    assert next(c for c in ok.checks if c.name == "Mark sheet completeness").result == "pass"
    stub(reading({s: (m, 95) for s, m in SIX.items() if s != "Biology"}))
    bad = run(SIX)
    comp = next(c for c in bad.checks if c.name == "Mark sheet completeness")
    assert comp.result == "fail" and "Biology" in comp.detail


def test_ac9_auto_cleared_only_when_everything_passes(stub):
    stub(reading({s: (m, 95) for s, m in SIX.items()}))
    res = run(SIX)
    assert res.status == v.AUTO_CLEARED
    assert res.issue_count == 0


def test_ac9_one_bad_photo_rule_means_review(stub):
    stub(reading({s: (m, 95) for s, m in SIX.items()}))
    res = run(SIX, photo=portrait(180, 220))
    assert res.status == v.NEEDS_REVIEW
    assert res.issue_count >= 1


def test_ac9_there_is_no_automatic_reject(stub):
    stub(reading({s: (0, 95) for s in SIX}))
    res = run(SIX, photo=b"garbage")
    assert res.status in {v.AUTO_CLEARED, v.NEEDS_REVIEW}
    assert res.status == v.NEEDS_REVIEW


def test_tolerance_setting_is_respected(stub, monkeypatch):
    sheet = dict(SIX, Mathematics=86)
    stub(reading({s: (m, 95) for s, m in sheet.items()}))
    loose = dict(DEFAULT_SETTINGS, mark_tolerance=1)
    res = v.validate_application(SIX, SHEET, GOOD_PHOTO, "tn_hsc", loose)
    assert row(res, "Mathematics").result == "match"


def test_unknown_template_is_review_not_crash():
    res = v.validate_application(SIX, SHEET, GOOD_PHOTO, "no_such_board", DEFAULT_SETTINGS)
    assert res.status == v.NEEDS_REVIEW


def test_real_sheet_end_to_end_with_planted_mismatch():
    """Integration: a real synthetic sheet through OCR, with one planted mismatch."""
    import random
    from dataset.generator import make_student, render_marksheet
    from engine.templates_registry import get_template
    tpl = get_template("tn_hsc")
    student = make_student(tpl, random.Random(11), 0)
    buf = io.BytesIO()
    render_marksheet(tpl, student).save(buf, "PNG")
    entered = {s["subject"]: s["total"] for s in student["subjects"]}
    first = next(iter(entered))
    entered[first] = (entered[first] + 7) % 101
    res = v.validate_application(entered, buf.getvalue(), GOOD_PHOTO, "tn_hsc", DEFAULT_SETTINGS)
    assert row(res, first).result == "mismatch"
    assert sum(c.result == "match" for c in res.checks) == len(entered) - 1
    assert res.status == v.NEEDS_REVIEW
