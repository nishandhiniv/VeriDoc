import io
import random

from dataset.generator import draw_portrait, make_student, render_marksheet
from engine.templates_registry import get_template


def sample_sheet(template_id="tn_hsc", seed=7):
    template = get_template(template_id)
    student = make_student(template, random.Random(seed), 0)
    buf = io.BytesIO()
    render_marksheet(template, student).save(buf, "PNG")
    return buf.getvalue(), {s["subject"]: s["total"] for s in student["subjects"]}, student


def sample_photo(w=600, h=800, fmt="JPEG"):
    buf = io.BytesIO()
    draw_portrait(w, h, random.Random(1)).save(buf, fmt, **({"quality": 90} if fmt == "JPEG" else {}))
    return buf.getvalue()


def details_form(board="tn_hsc", marks=None, **overrides):
    form = {"full_name": "Priya Raman", "date_of_birth": "2007-05-12", "contact": "priya@example.com",
            "board": board, "register_number": "1234567"}
    for i, (subject, mark) in enumerate((marks or {}).items()):
        form[f"subject_{i}"] = subject
        form[f"mark_{i}"] = str(mark)
    form.update(overrides)
    return form


def submit_application(client, marks, sheet, photo, board="tn_hsc"):
    client.post("/apply", data=details_form(board, marks))
    client.post("/apply/uploads", data={"marksheet": (io.BytesIO(sheet), "sheet.png"),
                                        "photo": (io.BytesIO(photo), "me.jpg")},
                content_type="multipart/form-data")
    return client.post("/apply/review")


def login(client, role="reviewer"):
    email = "reviewer@veridoc.test" if role == "reviewer" else "admin@veridoc.test"
    password = "reviewer-pass-123" if role == "reviewer" else "admin-pass-123"
    return client.post("/staff/login", data={"email": email, "password": password})
