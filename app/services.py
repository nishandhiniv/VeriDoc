"""Glue between the web app and the validation engine."""
import io
import secrets
from pathlib import Path

from flask import current_app
from PIL import Image

from engine import MAX_PIXELS
from engine.validate import validate_application

from .models import Application, CheckResult, EnteredMark, db, utcnow
from .settings_store import load_settings

PDF_MAGIC = b"%PDF"


class UploadError(ValueError):
    pass


def inspect_upload(data, settings):
    """Block only files that can't be processed at all (FR-A04). Returns the image format."""
    cap = settings["upload_hard_cap_mb"]
    if len(data) > cap * 1024 * 1024:
        raise UploadError(f"This file is larger than {cap} MB. Choose a smaller file.")
    if not data:
        raise UploadError("The file is empty. Choose the file again.")
    if data.startswith(PDF_MAGIC):
        raise UploadError("PDF files can't be checked yet. Upload a photo or scan as JPG or PNG.")
    try:
        img = Image.open(io.BytesIO(data))
        too_big = img.width * img.height > MAX_PIXELS
        img.verify()
    except Exception:  # noqa: BLE001 - includes PIL's own decompression-bomb error
        raise UploadError("This file isn't an image, or is far too large to process. Upload a JPG or PNG.") from None
    if too_big:
        raise UploadError("This image has too many pixels to process. Upload a smaller photo or scan.")
    return img.format


EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "BMP": "bmp", "WEBP": "webp", "TIFF": "tif"}


def store_upload(data, fmt):
    """Save with a random server-side name (NFR-06). Never uses the client's file name."""
    name = f"{secrets.token_hex(16)}.{EXTENSIONS.get(fmt, 'img')}"
    (Path(current_app.config["UPLOAD_DIR"]) / name).write_bytes(data)
    return name


def upload_path(name):
    base = Path(current_app.config["UPLOAD_DIR"]).resolve()
    path = (base / name).resolve()
    if path.parent != base:
        raise FileNotFoundError(name)
    return path


def run_validation(application, settings=None):
    """Run the engine and store every report row (FR-R07: results are stored, not recomputed)."""
    settings = settings or load_settings()
    entered = {m.subject: m.mark for m in application.marks}
    result = validate_application(
        entered,
        upload_path(application.marksheet_file).read_bytes(),
        upload_path(application.photo_file).read_bytes(),
        application.board,
        settings,
    )
    application.checks.clear()
    for i, check in enumerate(result.checks):
        application.checks.append(CheckResult(
            section=check.section, name=check.name, result=check.result, entered=check.entered,
            uploaded=check.uploaded, detail=check.detail, rule=check.rule, confidence=check.confidence,
            position=i, is_issue=check.is_issue,
        ))
    application.auto_status = result.status
    application.issue_count = result.issue_count
    application.validated_at = utcnow()
    return result


def create_application(details, marks, marksheet_file, photo_file, original_names=(None, None), is_demo=False):
    app = Application(
        full_name=details["full_name"], date_of_birth=details["date_of_birth"], contact=details["contact"],
        board=details["board"], register_number=details["register_number"],
        marksheet_file=marksheet_file, photo_file=photo_file,
        marksheet_original_name=original_names[0], photo_original_name=original_names[1], is_demo=is_demo,
    )
    for i, (subject, mark) in enumerate(marks):
        app.marks.append(EnteredMark(subject=subject, mark=mark, position=i))
    db.session.add(app)
    db.session.flush()
    app.reference = f"VD-{app.created_at.year}-{app.id:05d}"
    run_validation(app)
    db.session.commit()
    return app
