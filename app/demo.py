"""Demo applications seeded on startup (US-13 AC1, FR-S04).

Each one goes through the real validation engine; nothing here fakes a result.
Render's free disk resets on restart, so this recreates the demo whenever the
database has no demo applications.
"""
import io
import logging
import random
import threading
from datetime import date

from dataset.generator import degrade, draw_portrait, make_student, render_marksheet
from engine.templates_registry import get_template

from .models import Application, db
from .services import create_application, store_upload

log = logging.getLogger(__name__)

# (template, seed, scenario, photo size). Scenarios produce a realistic mix for the queue.
DEMO_CASES = [
    ("tn_hsc", 101, "correct", (600, 800)),
    ("tn_hsc", 102, "mismatch", (600, 800)),
    ("tn_hsc", 103, "not_entered", (600, 800)),
    ("tn_hsc", 104, "correct_degraded", (450, 600)),
    ("tn_hsc", 105, "correct", (180, 220)),          # catalogue example: photo too small
    ("tn_hsc", 106, "wrong_board", (600, 800)),      # CBSE sheet uploaded as TN HSC
    ("cbse_xii", 201, "correct", (600, 800)),
    ("cbse_xii", 202, "mismatch", (750, 1000)),
]


def _png(img, fmt="PNG"):
    buf = io.BytesIO()
    img.save(buf, fmt, **({"quality": 90} if fmt == "JPEG" else {}))
    return buf.getvalue()


def build_case(template_id, seed, scenario, photo_size):
    rng = random.Random(seed)
    template = get_template(template_id)
    sheet_template = get_template("cbse_xii") if scenario == "wrong_board" else template
    student = make_student(sheet_template, rng, 0)
    if scenario == "wrong_board":
        own = make_student(template, rng, 0)
        marks = [(s["subject"], s["total"]) for s in own["subjects"]]
    else:
        marks = [(s["subject"], s["total"]) for s in student["subjects"]]
    if scenario == "mismatch":
        subject, mark = marks[1]
        marks[1] = (subject, mark + 3 if mark <= 97 else mark - 3)
    elif scenario == "not_entered":
        marks = marks[:-1]
    img = render_marksheet(sheet_template, student)
    sheet_fmt = "PNG"
    if scenario == "correct_degraded":
        img, _ = degrade(img, rng)
        sheet_fmt = "JPEG"
    photo = draw_portrait(*photo_size, rng)
    details = {"full_name": student["name"], "date_of_birth": date.fromisoformat(student["date_of_birth"]),
               "contact": f"{student['name'].split()[0].lower()}@example.com", "board": template_id,
               "register_number": student["register_number"]}
    return details, marks, (_png(img, sheet_fmt), sheet_fmt), (_png(photo, "JPEG"), "JPEG")


def seed_demo_applications(app):
    with app.app_context():
        if Application.query.filter_by(is_demo=True).first():
            return
        created = 0
        for template_id, seed, scenario, photo_size in DEMO_CASES:
            if get_template(template_id) is None:
                continue
            try:
                details, marks, (sheet, sheet_fmt), (photo, photo_fmt) = build_case(
                    template_id, seed, scenario, photo_size)
                create_application(details, marks, store_upload(sheet, sheet_fmt), store_upload(photo, photo_fmt),
                                   original_names=(f"demo-{scenario}-marksheet", "demo-photo.jpg"), is_demo=True)
                created += 1
            except Exception:  # noqa: BLE001 - a broken demo case must never stop the site starting
                log.exception("Demo case %s/%s failed", template_id, scenario)
                db.session.rollback()
        log.info("Seeded %d demo applications", created)


def start_demo_seeding(app):
    if app.config.get("SEED_DEMO_ASYNC"):
        threading.Thread(target=seed_demo_applications, args=(app,), daemon=True, name="demo-seed").start()
    else:
        seed_demo_applications(app)
