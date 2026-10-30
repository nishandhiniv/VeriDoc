"""Whole-application validation (US-06, FR-V06–V08, V11, R01).

Fail-safe rule (NFR-03): an application is AUTO_CLEARED only when every single
check is clean. Low OCR confidence, an unknown layout or any processing error
sends it to NEEDS_REVIEW. There is no automatic reject.
"""
import io
import logging
from dataclasses import dataclass, field

from PIL import Image

from .marksheet import read_marksheet
from .photo import check_photo
from .results import Check
from .templates_registry import get_template

log = logging.getLogger(__name__)

AUTO_CLEARED = "auto_cleared"
NEEDS_REVIEW = "needs_review"


@dataclass
class ValidationResult:
    checks: list = field(default_factory=list)
    status: str = NEEDS_REVIEW
    issue_count: int = 0
    seconds: float = 0.0


def check_marksheet_file(data, settings):
    """The uploaded mark sheet file itself: an image of an allowed type and size."""
    max_bytes = settings["marksheet_max_mb"] * 1024 * 1024
    try:
        fmt = Image.open(io.BytesIO(data)).format
    except Exception:  # noqa: BLE001
        fmt = None
    allowed = settings["marksheet_formats"]
    size = f"{len(data) / 1024 / 1024:.1f} MB"
    return [
        Check("marksheet", "Mark sheet file format", "pass" if fmt in allowed else "fail",
              detail=fmt or "not a readable image", rule=" or ".join(allowed)),
        Check("marksheet", "Mark sheet file size", "pass" if len(data) <= max_bytes else "fail",
              detail=size, rule=f"up to {settings['marksheet_max_mb']} MB"),
    ]


def compare_marks(entered, sheet, settings):
    """Entered vs. uploaded, subject by subject."""
    threshold = settings["ocr_confidence_min"]
    tolerance = settings["mark_tolerance"]
    checks = []
    for subject, mark in entered.items():
        read = sheet.marks.get(subject)
        if read is None:
            checks.append(Check("marks", subject, "missing", entered=str(mark), uploaded="—",
                                detail=f"Entered: {mark}, not found on the uploaded mark sheet",
                                rule="subject must appear on the mark sheet"))
        elif read.value is None or read.confidence < threshold:
            seen = "nothing readable" if read.value is None else str(read.value)
            why = read.note or f"OCR confidence {read.confidence:.0f} is below {threshold}"
            checks.append(Check("marks", subject, "unreadable", entered=str(mark), uploaded="?",
                                confidence=read.confidence,
                                detail=f"Entered: {mark}, uploaded value not certain (read {seen}; {why})",
                                rule=f"OCR confidence at least {threshold}"))
        elif abs(read.value - mark) <= tolerance:
            checks.append(Check("marks", subject, "match", entered=str(mark), uploaded=str(read.value),
                                confidence=read.confidence, detail=f"Entered: {mark}, Uploaded: {read.value}",
                                rule="exact match" if tolerance == 0 else f"within ±{tolerance}"))
        else:
            checks.append(Check("marks", subject, "mismatch", entered=str(mark), uploaded=str(read.value),
                                confidence=read.confidence, detail=f"Entered: {mark}, Uploaded: {read.value}",
                                rule="exact match" if tolerance == 0 else f"within ±{tolerance}"))
    for subject, read in sheet.marks.items():
        if subject not in entered:
            shown = str(read.value) if read.value is not None else "?"
            checks.append(Check("marks", subject, "not_entered", entered="—", uploaded=shown,
                                confidence=read.confidence,
                                detail=f"On the mark sheet ({shown}) but not entered in the form",
                                rule="every subject on the mark sheet must be entered"))
    return checks


def completeness(entered, sheet):
    missing = [s for s in entered if s not in sheet.marks]
    extra = [s for s in sheet.marks if s not in entered]
    if not missing and not extra:
        return Check("marksheet", "Mark sheet completeness", "pass",
                     detail="All entered subjects are on the mark sheet, and none are left out",
                     rule="entered subjects = subjects on the mark sheet")
    parts = []
    if missing:
        parts.append("not on the sheet: " + ", ".join(missing))
    if extra:
        parts.append("on the sheet but not entered: " + ", ".join(extra))
    text = "; ".join(parts)
    return Check("marksheet", "Mark sheet completeness", "fail", detail=text[0].upper() + text[1:],
                 rule="entered subjects = subjects on the mark sheet")


def unverified_marks(entered, why):
    return [Check("marks", subject, "review", entered=str(mark), uploaded="—",
                  detail=f"Entered: {mark}, not verified ({why})", rule="needs a human check")
            for subject, mark in entered.items()]


def validate_marks(entered, marksheet_bytes, template_id, settings):
    template = get_template(template_id)
    if template is None:
        return [Check("system", "Processing error: unknown board", "error",
                      detail=f"No template for '{template_id}'. Sent to manual review.")] \
            + unverified_marks(entered, "unknown board")
    checks = check_marksheet_file(marksheet_bytes, settings)
    try:
        sheet = read_marksheet(marksheet_bytes, template)
    except Exception as exc:  # noqa: BLE001 - fail-safe: never auto-clear on error (US-06 AC7)
        log.exception("Mark sheet processing failed")
        return checks + [Check("system", "Processing error: mark sheet", "error",
                               detail=f"The mark sheet could not be processed ({type(exc).__name__}). "
                                      "Sent to manual review.")] \
            + unverified_marks(entered, "mark sheet could not be processed")
    return mark_checks(entered, sheet, template, settings) + checks


def mark_checks(entered, sheet, template, settings):
    """Report rows for the marks, given a mark sheet reading (also used by the evaluation)."""
    if not sheet.layout_ok:
        return [Check("marksheet", "Mark sheet layout", "review", detail=sheet.reason,
                      rule=f"must be a recognisable {template['short_label']} mark sheet")] \
            + unverified_marks(entered, "mark sheet layout not recognised")
    return compare_marks(entered, sheet, settings) + [completeness(entered, sheet)]


def validate_application(entered, marksheet_bytes, photo_bytes, template_id, settings):
    import time

    started = time.perf_counter()
    try:
        checks = validate_marks(entered, marksheet_bytes, template_id, settings)
        checks += check_photo(photo_bytes, settings)
    except Exception as exc:  # noqa: BLE001 - last line of defence
        log.exception("Validation failed")
        checks = [Check("system", "Processing error", "error",
                        detail=f"Validation stopped unexpectedly ({type(exc).__name__}). Sent to manual review.")]
    issues = sum(1 for c in checks if c.is_issue)
    status = AUTO_CLEARED if checks and issues == 0 else NEEDS_REVIEW
    return ValidationResult(checks=checks, status=status, issue_count=issues,
                            seconds=time.perf_counter() - started)
