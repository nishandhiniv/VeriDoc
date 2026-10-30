"""Profile photo validation (US-04, FR-P01–P08).

Every check is a plain measurement compared with a configurable threshold.
No machine learning, no GenAI.
"""
import io
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps

from .results import Check

RULE_NAMES = ["File format", "File size", "Resolution", "Maximum dimensions",
              "Aspect ratio", "Orientation", "Brightness", "Sharpness"]

# Sharpness is measured on a grayscale copy that is (a) scaled down to at most
# this width, never up, because upscaling blurs, and (b) contrast-normalised, so
# a dark photo is not mistaken for a blurry one.
SHARPNESS_WIDTH = 600
NORMALISED_STD = 50.0


def _kb(n):
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def _result(ok):
    return "pass" if ok else "fail"


def measure(data):
    """Read the photo and return its measurements. Raises if it can't be decoded."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        img.load()
    img = ImageOps.exif_transpose(img)  # judge the photo as people will see it
    width, height = img.size
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    small = img.convert("L")
    if small.width > SHARPNESS_WIDTH:
        small = small.resize((SHARPNESS_WIDTH, max(1, round(height * SHARPNESS_WIDTH / width))))
    g = np.asarray(small, dtype=np.float64)
    g = (g - g.mean()) * (NORMALISED_STD / max(g.std(), 1e-6))
    sharpness = float(cv2.Laplacian(g, cv2.CV_64F).var())
    return {
        "format": fmt,
        "bytes": len(data),
        "width": width,
        "height": height,
        "ratio": width / height,
        "brightness": float(gray.mean()),
        "contrast": float(gray.std()),
        "sharpness": sharpness,
    }


def check_photo(data, settings):
    try:
        if not data:
            raise ValueError("empty file")
        m = measure(data)
    except Exception as exc:  # noqa: BLE001 - any decode failure must go to review (NFR-03)
        return [Check("photo", "Photo file", "error",
                      detail=f"The photo could not be read ({type(exc).__name__}). Sent to manual review.",
                      rule="photo must be a readable image")]

    s = settings
    allowed = s["photo_formats"]
    min_b, max_b = s["photo_min_kb"] * 1024, s["photo_max_kb"] * 1024
    ratio = round(m["ratio"], 3)
    wants_portrait = s["photo_orientation"] == "portrait"
    is_portrait = m["height"] > m["width"]

    return [
        Check("photo", "File format", _result(m["format"] in allowed),
              detail=m["format"] or "unknown", rule=" or ".join(allowed)),
        Check("photo", "File size", _result(min_b <= m["bytes"] <= max_b),
              detail=_kb(m["bytes"]), rule=f"{_kb(min_b)} to {_kb(max_b)}"),
        Check("photo", "Resolution",
              _result(m["width"] >= s["photo_min_width"] and m["height"] >= s["photo_min_height"]),
              detail=f"{m['width']} × {m['height']} px",
              rule=f"minimum {s['photo_min_width']} × {s['photo_min_height']} px"),
        Check("photo", "Maximum dimensions",
              _result(m["width"] <= s["photo_max_width"] and m["height"] <= s["photo_max_height"]),
              detail=f"{m['width']} × {m['height']} px",
              rule=f"maximum {s['photo_max_width']} × {s['photo_max_height']} px"),
        Check("photo", "Aspect ratio", _result(s["photo_ratio_min"] <= ratio <= s["photo_ratio_max"]),
              detail=f"{ratio:.2f} (width ÷ height)",
              rule=f"{s['photo_ratio_min']:.2f} to {s['photo_ratio_max']:.2f}"),
        Check("photo", "Orientation", _result(is_portrait if wants_portrait else not is_portrait),
              detail="portrait" if is_portrait else ("square" if m["width"] == m["height"] else "landscape"),
              rule=f"{s['photo_orientation']} (after EXIF rotation)"),
        Check("photo", "Brightness",
              _result(s["photo_brightness_min"] <= m["brightness"] <= s["photo_brightness_max"]),
              detail=f"{m['brightness']:.0f} average (0–255)",
              rule=f"{s['photo_brightness_min']} to {s['photo_brightness_max']}"),
        Check("photo", "Sharpness", _result(m["sharpness"] >= s["photo_sharpness_min"]),
              detail=f"{m['sharpness']:.0f} focus score",
              rule=f"at least {s['photo_sharpness_min']} (variance of Laplacian)"),
    ]
