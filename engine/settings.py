"""Default validation settings (Phase 2 §5).

Every value here is a 🔧 default chosen by the team, not confirmed by Maatram,
except the 300 x 400 minimum, which comes from the catalogue example. The web
app stores these in the database so they can change without code changes.
"""

DEFAULT_SETTINGS = {
    # Photo rules (FR-P01–P09)
    "photo_formats": ["JPEG", "PNG"],
    "photo_min_kb": 20,
    "photo_max_kb": 2048,
    "photo_min_width": 300,
    "photo_min_height": 400,
    "photo_max_width": 3000,
    "photo_max_height": 4000,
    "photo_ratio_min": 0.70,
    "photo_ratio_max": 0.85,
    "photo_orientation": "portrait",
    "photo_brightness_min": 70,
    "photo_brightness_max": 210,
    "photo_sharpness_min": 25,  # tuned on the synthetic set (blurred <= 1, sharp >= 67)
    "photo_contrast_min": 25,
    # Mark sheet file
    "marksheet_formats": ["JPEG", "PNG"],
    "marksheet_max_mb": 5,
    # Upload hard cap: the only size limit the form enforces (FR-A04)
    "upload_hard_cap_mb": 10,
    # OCR / comparison
    "ocr_confidence_min": 70,
    "mark_tolerance": 0,
    "name_match_min": 85,
}


def merged(overrides=None):
    """Defaults with any stored overrides applied."""
    values = dict(DEFAULT_SETTINGS)
    if overrides:
        values.update({k: v for k, v in overrides.items() if k in DEFAULT_SETTINGS})
    return values
