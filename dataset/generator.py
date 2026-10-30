"""Synthetic dataset generator (US-11, FR-E01–E04).

Creates fake mark sheets that follow the general structure of TN HSC and CBSE XII
statements (subject rows, mark columns, totals) and a labelled photo set. Every
name and number is invented; there are no logos, seals or real data (NFR-07).

Ground truth is written from the generator's own parameters, never by running
the validation engine, so the evaluation (US-12) is an independent check.

Usage:  python -m dataset.generator [OUTPUT_DIR]
"""
import io
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from engine.settings import DEFAULT_SETTINGS
from engine.templates_registry import get_template

SEED = 2026
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
PAGE_W, PAGE_H = 1240, 1754  # A4 at 150 dpi

FIRST_NAMES = ["Priya", "Karthik", "Meena", "Arun", "Divya", "Surya", "Kavya", "Vignesh", "Lakshmi",
               "Rahul", "Nandhini", "Harish", "Swetha", "Gokul", "Anitha", "Pranav", "Keerthana",
               "Dinesh", "Revathi", "Sanjay", "Aishwarya", "Madhan", "Janani", "Rohit"]
LAST_NAMES = ["Raman", "Kumar", "Subramanian", "Iyer", "Natarajan", "Krishnan", "Murugan", "Selvam",
              "Sharma", "Rajan", "Balaji", "Ganesan", "Pillai", "Venkat", "Srinivasan", "Mohan"]

# Planted-error pattern for each block of 10 records (40 % contain an error, FR-E03).
ERROR_PATTERN = [None, "mismatch", None, "missing", None, None, "not_entered", None, "mismatch2", None]


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def cbse_grade(total):
    for limit, grade in ((91, "A1"), (81, "A2"), (71, "B1"), (61, "B2"), (51, "C1"), (41, "C2"), (33, "D")):
        if total >= limit:
            return grade
    return "E"


# ---------------------------------------------------------------- students

def make_student(template, rng, index):
    stream = rng.choice(template["streams"])
    subjects = []
    for name in stream:
        info = next(s for s in template["subjects"] if s["name"] == name)
        total = rng.randint(38, 100)
        row = {"subject": name, "total": total}
        if template["has_subject_code"]:
            prac_max = info["max"] - info["theory_max"]
            prac = rng.randint(max(0, total - info["theory_max"]), min(prac_max, total))
            row.update(code=info["code"], theory=total - prac, practical=prac, grade=cbse_grade(total))
        subjects.append(row)
    digits = 8 if template["has_subject_code"] else 7
    return {
        "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        "register_number": str(rng.randint(10 ** (digits - 1), 10 ** digits - 1)),
        "date_of_birth": f"{rng.randint(2006, 2008)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        "subjects": subjects,
        "index": index,
    }


def plant_entered_marks(template, student, error, rng):
    """Return (entered marks, expected outcome per subject) for a planted error type."""
    entered = {s["subject"]: s["total"] for s in student["subjects"]}
    expected = {name: "match" for name in entered}

    def change(name):
        original = entered[name]
        delta = rng.choice([d for d in range(-15, 16) if d != 0 and 0 <= original + d <= 100])
        entered[name] = original + delta
        expected[name] = "mismatch"

    names = list(entered)
    if error == "mismatch":
        change(rng.choice(names))
    elif error == "mismatch2":
        for name in rng.sample(names, 2):
            change(name)
    elif error == "missing":
        extra = rng.choice([s["name"] for s in template["subjects"] if s["name"] not in entered])
        entered[extra] = rng.randint(40, 99)
        expected[extra] = "missing"
    elif error == "not_entered":
        dropped = rng.choice(names[2:])
        del entered[dropped]
        expected[dropped] = "not_entered"
    return entered, expected


# ---------------------------------------------------------------- mark sheets

def render_marksheet(template, student):
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    f_title, f_head, f_body, f_small = font(30, True), font(24, True), font(26), font(20)

    y = 90
    for line in template["title_lines"]:
        w = d.textlength(line, font=f_title if y == 90 else f_head)
        d.text(((PAGE_W - w) / 2, y), line, fill="black", font=f_title if y == 90 else f_head)
        y += 52
    note = "SPECIMEN FOR SOFTWARE TESTING - NOT A VALID CERTIFICATE"
    d.text(((PAGE_W - d.textlength(note, font=f_small)) / 2, y), note, fill=(90, 90, 90), font=f_small)
    y += 70

    dob = student["date_of_birth"].split("-")
    reg_label = "ROLL NO" if template["has_subject_code"] else "REGISTER NO"
    for label, value in (("NAME OF CANDIDATE", student["name"].upper()),
                         (reg_label, student["register_number"]),
                         ("DATE OF BIRTH", f"{dob[2]}/{dob[1]}/{dob[0]}")):
        d.text((100, y), f"{label}", fill="black", font=f_body)
        d.text((480, y), f": {value}", fill="black", font=f_body)
        y += 48
    y += 30

    if template["has_subject_code"]:
        cols = [("CODE", 100), ("SUBJECT", 190), ("THEORY", 600), ("PRAC/IA", 745), ("TOTAL", 905), ("GRADE", 1030)]
    else:
        cols = [("SUBJECT", 100), ("MAX", 700), ("MARKS OBTAINED", 860)]
    left, right, row_h = 80, PAGE_W - 80, 60
    top = y
    d.line([(left, y), (right, y)], fill="black", width=3)
    for title, x in cols:
        d.text((x, y + 16), title, fill="black", font=f_head)
    y += row_h
    d.line([(left, y), (right, y)], fill="black", width=2)

    for s in student["subjects"]:
        cells = ([s["code"], s["subject"].upper(), f"{s['theory']:02d}", f"{s['practical']:02d}",
                  f"{s['total']:03d}", s["grade"]] if template["has_subject_code"]
                 else [s["subject"].upper(), "100", f"{s['total']:03d}"])
        for (title, x), text in zip(cols, cells):
            d.text((x, y + 16), text, fill="black", font=f_body)
        y += row_h
        d.line([(left, y), (right, y)], fill=(120, 120, 120), width=1)

    grand = sum(s["total"] for s in student["subjects"])
    if template["has_subject_code"]:
        d.text((200, y + 16), "RESULT", fill="black", font=f_head)
        d.text((600, y + 16), "PASS", fill="black", font=f_head)
    else:
        d.text((100, y + 16), "TOTAL", fill="black", font=f_head)
        d.text((700, y + 16), str(100 * len(student["subjects"])), fill="black", font=f_head)
        d.text((860, y + 16), f"{grand:03d}", fill="black", font=f_head)
    y += row_h
    d.line([(left, y), (right, y)], fill="black", width=3)
    d.rectangle([(left, top), (right, y)], outline="black", width=2)

    d.text((100, y + 80), "Generated by the VeriDoc synthetic dataset tool. Fictional candidate.",
           fill=(90, 90, 90), font=f_small)
    return img


def degrade(img, rng):
    """Phone-photo style degradation: small skew, blur, low light, noise, JPEG artefacts."""
    angle = rng.uniform(-2.0, 2.0)
    out = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(235, 233, 225))
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.3)))
    out = ImageEnhance.Brightness(out).enhance(rng.uniform(0.62, 0.8))
    arr = np.asarray(out).astype(np.float32)
    np_rng = np.random.default_rng(rng.randint(0, 2 ** 31))
    arr += np_rng.normal(0, rng.uniform(6, 12), arr.shape)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=rng.randint(45, 65))
    return Image.open(io.BytesIO(buf.getvalue())), {"angle": round(angle, 2)}


# ---------------------------------------------------------------- photos

def draw_portrait(w, h, rng, brightness=1.0, blur=0.0):
    """A simple synthetic head-and-shoulders portrait with photographic noise."""
    np_rng = np.random.default_rng(rng.randint(0, 2 ** 31))
    bg = np.array(rng.choice([(205, 220, 235), (225, 225, 225), (200, 215, 205)]), dtype=np.float32)
    arr = np.ones((h, w, 3), dtype=np.float32) * bg
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    cx = w / 2
    skin = rng.choice([(176, 125, 95), (150, 105, 80), (198, 150, 118)])
    shirt = rng.choice([(40, 60, 110), (120, 30, 40), (30, 30, 30), (240, 240, 240)])
    d.ellipse([cx - w * 0.45, h * 0.70, cx + w * 0.45, h * 1.25], fill=shirt)
    d.rectangle([cx - w * 0.08, h * 0.52, cx + w * 0.08, h * 0.75], fill=skin)
    d.ellipse([cx - w * 0.21, h * 0.18, cx + w * 0.21, h * 0.62], fill=skin)
    d.ellipse([cx - w * 0.23, h * 0.13, cx + w * 0.23, h * 0.36], fill=(25, 20, 18))
    for ex in (-0.08, 0.08):
        d.ellipse([cx + w * ex - w * 0.025, h * 0.38, cx + w * ex + w * 0.025, h * 0.41], fill=(20, 20, 20))
    d.line([(cx - w * 0.06, h * 0.52), (cx + w * 0.06, h * 0.52)], fill=(110, 50, 50), width=max(2, w // 120))
    arr = np.asarray(img).astype(np.float32)
    arr += np_rng.normal(0, 9, arr.shape)  # sensor noise gives realistic detail and file size
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    return img


# Each spec: (id, width, height, format, options, intended defects)
PHOTO_SPECS = [
    ("valid_01", 600, 800, "JPEG", {}, []),
    ("valid_02", 450, 600, "JPEG", {}, []),
    ("valid_03", 750, 1000, "JPEG", {}, []),
    ("valid_04_min_boundary", 300, 400, "JPEG", {"quality": 95}, []),
    ("valid_05_png", 600, 800, "PNG", {}, []),
    ("valid_06_exif_rotated", 600, 800, "JPEG", {"exif_rotate": True}, []),
    ("valid_07", 900, 1200, "JPEG", {}, []),
    ("valid_08", 525, 700, "JPEG", {}, []),
    ("small_180x220", 180, 220, "JPEG", {"quality": 95}, ["min_resolution"]),
    ("small_240x320", 240, 320, "JPEG", {"quality": 95}, ["min_resolution"]),
    ("small_299x399", 299, 399, "JPEG", {"quality": 95}, ["min_resolution"]),
    ("huge_3200x4200", 3200, 4200, "JPEG", {"quality": 60}, ["max_dimensions"]),
    ("huge_3100x4000", 3100, 4000, "JPEG", {"quality": 60}, ["max_dimensions"]),
    ("filesize_large", 1500, 2000, "JPEG", {"quality": 100}, ["file_size"]),
    ("filesize_tiny", 300, 400, "JPEG", {"quality": 2}, ["file_size"]),
    ("ratio_square", 700, 700, "JPEG", {}, ["aspect_ratio", "orientation"]),
    ("ratio_tall", 600, 900, "JPEG", {}, ["aspect_ratio"]),
    ("ratio_wide_portrait", 600, 700, "JPEG", {}, ["aspect_ratio"]),
    ("landscape_800x600", 800, 600, "JPEG", {}, ["aspect_ratio", "orientation"]),
    ("landscape_1000x750", 1000, 750, "JPEG", {}, ["aspect_ratio", "orientation"]),
    ("dark_01", 600, 800, "JPEG", {"brightness": 0.30}, ["brightness"]),
    ("dark_02", 450, 600, "JPEG", {"brightness": 0.25}, ["brightness"]),
    ("bright_01", 600, 800, "JPEG", {"brightness": 3.5}, ["brightness"]),
    ("bright_02", 450, 600, "JPEG", {"brightness": 4.0}, ["brightness"]),
    ("blurry_01", 900, 1200, "JPEG", {"blur": 6, "quality": 97}, ["sharpness"]),
    ("blurry_02", 750, 1000, "JPEG", {"blur": 5, "quality": 97}, ["sharpness"]),
    ("blurry_03", 750, 1000, "JPEG", {"blur": 8}, ["sharpness"]),
    ("format_gif", 600, 800, "GIF", {}, ["format"]),
    ("format_bmp", 450, 600, "BMP", {}, ["format"]),
    ("format_webp", 600, 800, "WEBP", {}, ["format"]),
]
PHOTO_RULES = ["format", "file_size", "min_resolution", "max_dimensions",
               "aspect_ratio", "orientation", "brightness", "sharpness"]
EXT = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "BMP": "bmp", "WEBP": "webp"}


def make_photo(spec, rng):
    pid, w, h, fmt, opts, defects = spec
    if opts.get("flat"):
        img = Image.new("RGB", (w, h), (210, 210, 210))
        ImageDraw.Draw(img).ellipse([w * 0.3, h * 0.2, w * 0.7, h * 0.6], fill=(180, 130, 100))
    else:
        img = draw_portrait(w, h, rng, brightness=opts.get("brightness", 1.0), blur=opts.get("blur", 0))
    buf = io.BytesIO()
    save_kwargs = {}
    if fmt == "JPEG":
        save_kwargs["quality"] = opts.get("quality", 88)
    if opts.get("exif_rotate"):
        # Store pixels sideways and tell viewers to rotate back (EXIF orientation 6).
        img = img.transpose(Image.Transpose.ROTATE_90)
        exif = Image.Exif()
        exif[0x0112] = 6
        save_kwargs["exif"] = exif.tobytes()
    if fmt == "GIF":
        img = img.convert("P", palette=Image.Palette.ADAPTIVE)
    img.save(buf, fmt, **save_kwargs)
    return buf.getvalue(), defects


def expected_photo_labels(w, h, fmt, nbytes, defects, settings=DEFAULT_SETTINGS):
    """Ground truth per rule. Measurable properties come from the file's known
    parameters; brightness and sharpness come from how the photo was generated."""
    ratio = w / h
    passes = {
        "format": fmt in settings["photo_formats"],
        "file_size": settings["photo_min_kb"] * 1024 <= nbytes <= settings["photo_max_kb"] * 1024,
        "min_resolution": w >= settings["photo_min_width"] and h >= settings["photo_min_height"],
        "max_dimensions": w <= settings["photo_max_width"] and h <= settings["photo_max_height"],
        "aspect_ratio": settings["photo_ratio_min"] <= round(ratio, 3) <= settings["photo_ratio_max"],
        "orientation": h > w,
        "brightness": "brightness" not in defects,
        "sharpness": "sharpness" not in defects,
    }
    return {rule: ("pass" if passes[rule] else "fail") for rule in PHOTO_RULES}


# ---------------------------------------------------------------- main

def generate(out_dir, sheets_per_template=20, clean_per_template=10, seed=SEED, photos=True):
    out_dir = Path(out_dir)
    (out_dir / "marksheets").mkdir(parents=True, exist_ok=True)
    (out_dir / "photos").mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    truth = {"seed": seed, "marksheets": [], "photos": []}

    for template_id in ("tn_hsc", "cbse_xii"):
        template = get_template(template_id)
        for i in range(sheets_per_template):
            variant = "clean" if i < clean_per_template else "degraded"
            student = make_student(template, rng, i)
            error = ERROR_PATTERN[i % len(ERROR_PATTERN)]
            entered, expected = plant_entered_marks(template, student, error, rng)
            img = render_marksheet(template, student)
            meta = {}
            if variant == "degraded":
                img, meta = degrade(img, rng)
            file_name = f"{template_id}_{i + 1:02d}_{variant}.png" if variant == "clean" \
                else f"{template_id}_{i + 1:02d}_{variant}.jpg"
            path = out_dir / "marksheets" / file_name
            if variant == "clean":
                img.save(path, "PNG", optimize=True)
            else:
                img.save(path, "JPEG", quality=90)
            truth["marksheets"].append({
                "file": f"marksheets/{file_name}", "template": template_id, "variant": variant,
                "student": {k: v for k, v in student.items() if k != "index"},
                "sheet_marks": {s["subject"]: s["total"] for s in student["subjects"]},
                "entered_marks": entered, "expected": expected, "planted_error": error, **meta,
            })

    if photos:
        for spec in PHOTO_SPECS:
            data, defects = make_photo(spec, rng)
            pid, w, h, fmt, opts, _ = spec
            name = f"{pid}.{EXT[fmt]}"
            (out_dir / "photos" / name).write_bytes(data)
            truth["photos"].append({
                "file": f"photos/{name}", "width": w, "height": h, "format": fmt, "bytes": len(data),
                "intended_defects": defects,
                "expected": expected_photo_labels(w, h, fmt, len(data), defects),
            })

    (out_dir / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    return truth


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/dataset")
    result = generate(target)
    print(f"Wrote {len(result['marksheets'])} mark sheets and {len(result['photos'])} photos to {target}")
