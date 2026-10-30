"""US-01 details & marks, US-02 uploads/review/submit, US-03 home page."""
import io
import re

import pytest

from app.models import Application
from app.settings_store import save_setting
from tests.helpers import details_form, sample_photo, sample_sheet, submit_application

SIX = {"Tamil": 80, "English": 92, "Mathematics": 85, "Physics": 70, "Chemistry": 66, "Biology": 90}


# ---------------------------------------------------------------- US-01

def test_us01_ac1_form_opens_without_login(client):
    resp = client.get("/apply")
    assert resp.status_code == 200
    assert b"Your details and marks" in resp.data
    assert b"Sign in" not in resp.data


def test_us01_ac2_subjects_limited_to_chosen_board(client):
    resp = client.post("/apply", data=details_form("tn_hsc", {"Business Studies": 70, **SIX}))
    assert resp.status_code == 400
    assert b"isn&#39;t a TN HSC subject" in resp.data


def test_us01_ac2_subject_count_within_template_limits(client):
    resp = client.post("/apply", data=details_form("tn_hsc", {"Tamil": 80, "English": 70}))
    assert resp.status_code == 400
    assert b"Enter between 5 and 6 subjects" in resp.data


@pytest.mark.parametrize("field,message", [
    ("full_name", b"Enter your full name"), ("date_of_birth", b"Enter your date of birth"),
    ("contact", b"Enter an email address or a 10-digit mobile number"),
    ("board", b"Choose your board and exam"), ("register_number", b"Enter your register or roll number")])
def test_us01_ac3_required_fields_show_message_next_to_field(client, field, message):
    form = details_form("tn_hsc", SIX)
    form[field] = ""
    resp = client.post("/apply", data=form)
    assert resp.status_code == 400
    assert message in resp.data
    assert f'id="{field}-error"'.encode() in resp.data
    assert f'aria-describedby="{field}'.encode() in resp.data


def test_us01_ac3_mark_without_subject(client):
    form = details_form("tn_hsc", SIX)
    form["subject_0"] = ""
    resp = client.post("/apply", data=form)
    assert b"Choose the subject for this mark" in resp.data


@pytest.mark.parametrize("bad", ["101", "-1", "85.5", "abc"])
def test_us01_ac4_mark_range_and_whole_numbers(client, bad):
    resp = client.post("/apply", data=details_form("tn_hsc", dict(SIX, Tamil=bad)))
    assert resp.status_code == 400
    assert b"Enter a whole number from 0 to 100" in resp.data


def test_us01_ac5_duplicate_subject(client):
    form = details_form("tn_hsc", SIX)
    form["subject_1"] = "Tamil"
    resp = client.post("/apply", data=form)
    assert b"Each subject can only be entered once" in resp.data


def test_us01_ac6_labels_and_mobile_viewport(client):
    html = client.get("/apply").get_data(as_text=True)
    assert 'name="viewport"' in html
    for field_id in ["full_name", "date_of_birth", "contact", "board", "register_number", "subject_0", "mark_0"]:
        assert f'for="{field_id}"' in html and f'id="{field_id}"' in html


def test_us01_valid_details_go_to_uploads(client):
    resp = client.post("/apply", data=details_form("tn_hsc", SIX))
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/apply/uploads")


# ---------------------------------------------------------------- US-02

@pytest.fixture
def at_uploads(client):
    client.post("/apply", data=details_form("tn_hsc", SIX))
    return client


def upload(client, sheet, photo, sheet_name="sheet.png", photo_name="me.jpg"):
    return client.post("/apply/uploads", data={"marksheet": (io.BytesIO(sheet), sheet_name),
                                               "photo": (io.BytesIO(photo), photo_name)},
                       content_type="multipart/form-data")


def test_us02_ac1_photo_breaking_rules_is_still_accepted(at_uploads):
    sheet, _, _ = sample_sheet()
    resp = upload(at_uploads, sheet, sample_photo(180, 220))
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/apply/review")


def test_us02_ac2_non_image_renamed_jpg_rejected_by_content(at_uploads):
    resp = upload(at_uploads, b"just some text, honestly", sample_photo(), sheet_name="sheet.jpg")
    assert resp.status_code == 400
    assert b"This file isn&#39;t an image" in resp.data


def test_us02_pdf_gets_clear_message(at_uploads):
    resp = upload(at_uploads, b"%PDF-1.7 fake", sample_photo(), sheet_name="sheet.pdf")
    assert b"PDF files can&#39;t be checked yet" in resp.data


def test_us02_ac3_hard_cap(app, at_uploads):
    with app.app_context():
        save_setting("upload_hard_cap_mb", 1)
    big = b"\xff\xd8" + b"0" * (1024 * 1024 + 10)
    resp = upload(at_uploads, big, sample_photo())
    assert resp.status_code == 400
    assert b"larger than 1 MB" in resp.data


def test_us02_ac4_review_screen_shows_everything_with_edit_links(at_uploads):
    sheet, _, _ = sample_sheet()
    upload(at_uploads, sheet, sample_photo())
    html = at_uploads.get("/apply/review").get_data(as_text=True)
    for text in ["Priya Raman", "2007-05-12", "priya@example.com", "1234567", "Tamil", "92", "sheet.png", "me.jpg"]:
        assert text in html
    assert html.count(">Edit<") == 3
    assert at_uploads.get("/apply/file/marksheet").status_code == 200


def test_us02_ac4_edit_keeps_data(at_uploads):
    sheet, _, _ = sample_sheet()
    upload(at_uploads, sheet, sample_photo())
    html = at_uploads.get("/apply").get_data(as_text=True)
    assert 'value="Priya Raman"' in html and 'value="92"' in html
    # Saving the details again goes straight back to review, files kept.
    resp = at_uploads.post("/apply", data=details_form("tn_hsc", SIX))
    assert resp.headers["Location"].endswith("/apply/review")


def test_us02_ac5_submit_creates_application_with_reference(app, client):
    sheet, marks, _ = sample_sheet()
    resp = submit_application(client, marks, sheet, sample_photo())
    assert resp.status_code == 302
    page = client.get("/apply/submitted").get_data(as_text=True)
    ref = re.search(r"VD-\d{4}-\d{5}", page).group(0)
    with app.app_context():
        application = Application.query.filter_by(reference=ref).one()
        assert application.auto_status in ("auto_cleared", "needs_review")
        assert len(application.checks) > 0


def test_us02_ac6_random_server_file_names_and_notice(app, client):
    sheet, marks, _ = sample_sheet()
    html = client.get("/apply/uploads", follow_redirects=True).get_data(as_text=True)
    submit_application(client, marks, sheet, sample_photo())
    with app.app_context():
        a = Application.query.one()
        assert re.fullmatch(r"[0-9a-f]{32}\.(png|jpg)", a.marksheet_file)
        assert a.marksheet_file != "sheet.png"
    assert "do not upload real documents" in client.get("/").get_data(as_text=True).lower()


def test_us02_other_applicants_files_not_reachable(client):
    assert client.get("/apply/file/marksheet").status_code == 404


# ---------------------------------------------------------------- US-03

def test_us03_ac1_home_lists_documents_and_photo_rules(client):
    html = client.get("/").get_data(as_text=True)
    for text in ["What you need", "Photo rules", "JPEG or PNG", "300 × 400", "3000 × 4000",
                 "0.70", "0.85", "Portrait", "Start application"]:
        assert text in html


def test_us03_ac2_rules_are_read_from_settings(app, client):
    with app.app_context():
        save_setting("photo_min_width", 350)
        save_setting("photo_min_height", 450)
    html = client.get("/").get_data(as_text=True)
    assert "350 × 450" in html and "300 × 400" not in html


def test_us02_decompression_bomb_rejected(at_uploads):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("1", (8000, 8000)).save(buf, "PNG")  # 64 million pixels, tiny file
    resp = upload(at_uploads, buf.getvalue(), sample_photo())
    assert resp.status_code == 400
    assert b"too many pixels" in resp.data or b"far too large" in resp.data
