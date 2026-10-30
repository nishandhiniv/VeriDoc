"""US-04 Photo validation (FR-P01–P08). Written before engine/photo.py."""
import io
import random

import numpy as np
import pytest
from PIL import Image

from dataset.generator import draw_portrait

from engine.photo import RULE_NAMES, check_photo
from engine.settings import DEFAULT_SETTINGS


def portrait(w=600, h=800, fmt="JPEG", brightness=None, blur=0, seed=1, **save):
    """A structured head-and-shoulders drawing with sensor noise, like a real photo."""
    img = draw_portrait(w, h, random.Random(seed), blur=blur)
    if brightness is not None:
        arr = np.asarray(img, dtype=np.float32)
        arr = (arr - arr.mean()) * 0.3 + brightness
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    if fmt == "JPEG":
        save.setdefault("quality", 90)
    img.save(buf, fmt, **save)
    return buf.getvalue()


def by_name(checks):
    return {c.name: c for c in checks}


def test_ac1_eight_results_each_with_value_and_rule():
    checks = check_photo(portrait(), DEFAULT_SETTINGS)
    assert [c.name for c in checks] == RULE_NAMES
    assert len(checks) == 8
    for c in checks:
        assert c.section == "photo"
        assert c.result in {"pass", "fail"}
        assert c.detail and c.rule


def test_ac1_valid_photo_passes_everything():
    assert all(c.result == "pass" for c in check_photo(portrait(), DEFAULT_SETTINGS))


def test_ac2_resolution_180x220_fails_with_catalogue_wording():
    res = by_name(check_photo(portrait(180, 220), DEFAULT_SETTINGS))["Resolution"]
    assert res.result == "fail"
    assert res.detail == "180 × 220 px"
    assert res.rule == "minimum 300 × 400 px"


def test_ac2_resolution_600x800_passes():
    assert by_name(check_photo(portrait(600, 800), DEFAULT_SETTINGS))["Resolution"].result == "pass"


def test_ac3_landscape_fails_orientation():
    assert by_name(check_photo(portrait(800, 600), DEFAULT_SETTINGS))["Orientation"].result == "fail"


def test_ac3_exif_rotation_applied_before_judging():
    # Pixels stored sideways (800 x 600) with EXIF orientation 6 = portrait 600 x 800 when viewed.
    rng = np.random.default_rng(3)
    img = Image.fromarray(np.clip(rng.normal(130, 40, (600, 800, 3)), 0, 255).astype(np.uint8))
    exif = Image.Exif()
    exif[0x0112] = 6
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90, exif=exif.tobytes())
    checks = by_name(check_photo(buf.getvalue(), DEFAULT_SETTINGS))
    assert checks["Orientation"].result == "pass"
    assert checks["Resolution"].detail == "600 × 800 px"


def test_ac4_dark_image_fails_brightness():
    res = by_name(check_photo(portrait(brightness=30), DEFAULT_SETTINGS))["Brightness"]
    assert res.result == "fail"


def test_ac4_overexposed_image_fails_brightness():
    assert by_name(check_photo(portrait(brightness=240), DEFAULT_SETTINGS))["Brightness"].result == "fail"


def test_ac4_blurred_image_fails_sharpness():
    assert by_name(check_photo(portrait(blur=6), DEFAULT_SETTINGS))["Sharpness"].result == "fail"


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "WEBP"])
def test_ac5_only_jpeg_png_pass_format(fmt):
    assert by_name(check_photo(portrait(fmt=fmt), DEFAULT_SETTINGS))["File format"].result == "fail"


def test_ac5_png_passes_format():
    assert by_name(check_photo(portrait(fmt="PNG"), DEFAULT_SETTINGS))["File format"].result == "pass"


@pytest.mark.parametrize("data", [b"", b"not an image at all", b"\xff\xd8\xff\xe0truncated"])
def test_ac6_unreadable_photo_is_processing_error_never_pass(data):
    checks = check_photo(data, DEFAULT_SETTINGS)
    assert len(checks) == 1
    assert checks[0].result == "error"
    assert checks[0].is_issue
    assert "review" in checks[0].detail.lower()


def test_ac7_thresholds_come_from_settings():
    data = portrait(600, 800)
    stricter = dict(DEFAULT_SETTINGS, photo_min_width=700, photo_min_height=900)
    assert by_name(check_photo(data, DEFAULT_SETTINGS))["Resolution"].result == "pass"
    assert by_name(check_photo(data, stricter))["Resolution"].result == "fail"


def test_file_size_limits():
    tiny = portrait(300, 400, quality=5, brightness=128)
    assert by_name(check_photo(tiny, DEFAULT_SETTINGS))["File size"].result == "fail"


def test_aspect_ratio_and_max_dimensions():
    checks = by_name(check_photo(portrait(600, 900), DEFAULT_SETTINGS))
    assert checks["Aspect ratio"].result == "fail"
    huge = by_name(check_photo(portrait(3100, 4000, quality=30), DEFAULT_SETTINGS))
    assert huge["Maximum dimensions"].result == "fail"
