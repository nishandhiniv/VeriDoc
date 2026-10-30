"""Applicant pages (US-01, US-02, US-03). No account needed (FR-A01)."""
import re
from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, send_file, session, url_for

from engine.templates_registry import all_templates, get_template

from .services import UploadError, create_application, inspect_upload, store_upload, upload_path
from .settings_store import load_settings

bp = Blueprint("public", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^(\+91[\s-]?)?[6-9]\d{9}$")
REGISTER_RE = re.compile(r"^[A-Za-z0-9]{4,20}$")
ROWS = 6  # subject rows shown on the form (largest max_subjects of any template)


def boards():
    return [{"id": t["id"], "label": t["label"], "short": t["short_label"], "min": t["min_subjects"],
             "max": t["max_subjects"], "subjects": [{"name": s["name"], "max": s["max"]} for s in t["subjects"]]}
            for t in all_templates().values()]


@bp.route("/")
def home():
    return render_template("public/home.html", rules=load_settings(), boards=boards())


# ------------------------------------------------------------------ step 1

def validate_details(form):
    """Return (clean data, errors). Errors are keyed by field name, written for the applicant."""
    errors, data = {}, {}
    name = " ".join(form.get("full_name", "").split())
    if not name:
        errors["full_name"] = "Enter your full name as it appears on your mark sheet."
    elif len(name) < 2 or len(name) > 120:
        errors["full_name"] = "Name must be between 2 and 120 characters."
    data["full_name"] = name

    dob_raw = form.get("date_of_birth", "").strip()
    data["date_of_birth"] = dob_raw
    if not dob_raw:
        errors["date_of_birth"] = "Enter your date of birth."
    else:
        try:
            dob = date.fromisoformat(dob_raw)
            if not (date(1950, 1, 1) <= dob <= date.today()):
                errors["date_of_birth"] = "Enter a real date of birth in the past."
        except ValueError:
            errors["date_of_birth"] = "Enter the date as day, month and year."

    contact = form.get("contact", "").strip()
    data["contact"] = contact
    if not contact:
        errors["contact"] = "Enter an email address or a 10-digit mobile number."
    elif not (EMAIL_RE.match(contact) or PHONE_RE.match(contact.replace(" ", ""))):
        errors["contact"] = "Enter a valid email address or a 10-digit mobile number."

    board_id = form.get("board", "")
    data["board"] = board_id
    template = get_template(board_id)
    if template is None:
        errors["board"] = "Choose your board and exam."

    reg = form.get("register_number", "").strip()
    data["register_number"] = reg
    if not reg:
        errors["register_number"] = "Enter your register or roll number."
    elif not REGISTER_RE.match(reg):
        errors["register_number"] = "Use 4 to 20 letters or digits, without spaces."

    marks, seen = [], set()
    data["rows"] = []
    subject_max = {s["name"]: s["max"] for s in template["subjects"]} if template else {}
    for i in range(ROWS):
        subject = form.get(f"subject_{i}", "").strip()
        mark_raw = form.get(f"mark_{i}", "").strip()
        data["rows"].append({"subject": subject, "mark": mark_raw})
        if not subject and not mark_raw:
            continue
        if not subject:
            errors[f"subject_{i}"] = "Choose the subject for this mark."
            continue
        if template and subject not in subject_max:
            errors[f"subject_{i}"] = f"{subject} isn't a {template['short_label']} subject. Choose from the list."
            continue
        if subject in seen:
            errors[f"subject_{i}"] = "Each subject can only be entered once."
            continue
        seen.add(subject)
        top = subject_max.get(subject, 100)
        if not re.fullmatch(r"\d{1,3}", mark_raw) or not (0 <= int(mark_raw) <= top):
            errors[f"mark_{i}"] = f"Enter a whole number from 0 to {top}."
            continue
        marks.append((subject, int(mark_raw)))

    if template and not any(k.startswith(("subject_", "mark_")) for k in errors):
        if not (template["min_subjects"] <= len(marks) <= template["max_subjects"]):
            errors["subjects"] = (f"Enter between {template['min_subjects']} and {template['max_subjects']} "
                                  f"subjects for {template['short_label']}. You entered {len(marks)}.")
    data["marks"] = marks
    return data, errors


@bp.route("/apply", methods=["GET", "POST"])
def apply_details():
    draft = session.get("draft", {})
    if request.method == "POST":
        data, errors = validate_details(request.form)
        if errors:
            return render_template("public/apply_details.html", data=data, errors=errors, boards=boards(),
                                   rows=ROWS), 400
        session["draft"] = {**draft, "details": {k: data[k] for k in
                                                ("full_name", "date_of_birth", "contact", "board", "register_number")},
                            "marks": data["marks"]}
        return redirect(url_for("public.review") if draft.get("files") else url_for("public.apply_uploads"))

    details = draft.get("details", {})
    rows = [{"subject": s, "mark": str(m)} for s, m in draft.get("marks", [])]
    rows += [{"subject": "", "mark": ""}] * (ROWS - len(rows))
    return render_template("public/apply_details.html", data={**details, "rows": rows}, errors={},
                           boards=boards(), rows=ROWS)


# ------------------------------------------------------------------ step 2

@bp.route("/apply/uploads", methods=["GET", "POST"])
def apply_uploads():
    draft = session.get("draft")
    if not draft or "details" not in draft:
        return redirect(url_for("public.apply_details"))
    files = dict(draft.get("files", {}))
    errors = {}
    if request.method == "POST":
        settings = load_settings()
        for kind in ("marksheet", "photo"):
            upload = request.files.get(kind)
            if upload and upload.filename:
                data = upload.read()
                try:
                    fmt = inspect_upload(data, settings)
                except UploadError as exc:
                    errors[kind] = str(exc)
                    continue
                files[kind] = {"stored": store_upload(data, fmt), "original": upload.filename[:200]}
            elif kind not in files:
                errors[kind] = ("Upload your mark sheet." if kind == "marksheet" else "Upload your profile photo.")
        draft["files"] = files
        session["draft"] = draft
        if not errors:
            return redirect(url_for("public.review"))
        return render_template("public/apply_uploads.html", files=files, errors=errors,
                               rules=settings), 400
    return render_template("public/apply_uploads.html", files=files, errors=errors, rules=load_settings())


@bp.route("/apply/file/<kind>")
def draft_file(kind):
    """Thumbnails for the applicant's own pending uploads only."""
    files = session.get("draft", {}).get("files", {})
    if kind not in ("marksheet", "photo") or kind not in files:
        abort(404)
    return send_file(upload_path(files[kind]["stored"]))


# ------------------------------------------------------------------ step 3

@bp.route("/apply/review", methods=["GET", "POST"])
def review():
    draft = session.get("draft", {})
    if "details" not in draft:
        return redirect(url_for("public.apply_details"))
    if set(draft.get("files", {})) != {"marksheet", "photo"}:
        return redirect(url_for("public.apply_uploads"))
    template = get_template(draft["details"]["board"])
    if request.method == "POST":
        d = draft["details"]
        details = {**d, "date_of_birth": date.fromisoformat(d["date_of_birth"])}
        files = draft["files"]
        application = create_application(
            details, [tuple(m) for m in draft["marks"]], files["marksheet"]["stored"], files["photo"]["stored"],
            original_names=(files["marksheet"]["original"], files["photo"]["original"]))
        session.pop("draft", None)
        session["submitted"] = application.reference
        return redirect(url_for("public.submitted"))
    return render_template("public/apply_review.html", draft=draft, template=template)


@bp.route("/apply/submitted")
def submitted():
    reference = session.get("submitted")
    if not reference:
        return redirect(url_for("public.home"))
    return render_template("public/submitted.html", reference=reference)
