"""Mark sheet reading (US-05 / US-07, FR-V01–V04).

Pipeline: decode → pre-process (OpenCV) → Tesseract OCR with word positions and
confidences → find the template's mark column → match subject names with fuzzy
string matching → re-read each mark digits-only and require both readings to agree.

Rules + OCR only; no Generative AI or LLMs (NFR-05).
"""
import io
import re
from dataclasses import dataclass, field

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps
from rapidfuzz import fuzz, process

SUBJECT_MATCH_MIN = 85      # fuzzy score needed to accept a subject name
KEYWORD_MATCH_MIN = 80      # fuzzy score for title / header keywords
TARGET_WIDTH = 2400         # OCR works best around 300 dpi for an A4 page
NUMBER_RE = re.compile(r"^\d{1,3}$")


@dataclass
class ReadMark:
    subject: str
    value: int = None
    confidence: float = 0.0
    raw: str = ""
    note: str = ""


@dataclass
class SheetReading:
    layout_ok: bool = False
    reason: str = ""
    title_found: bool = False
    header_found: bool = False
    marks: dict = field(default_factory=dict)  # subject name -> ReadMark
    seconds: float = 0.0


# ------------------------------------------------------------------ images

def load_image(data):
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    return np.asarray(img.convert("L"))


def preprocess(gray):
    """FR-V01: scale to ~300 dpi, denoise, and binarise."""
    h, w = gray.shape
    if w < TARGET_WIDTH:
        scale = TARGET_WIDTH / w
        gray = cv2.resize(gray, (TARGET_WIDTH, round(h * scale)), interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Normalise uneven lighting (phone photos) before a global Otsu threshold.
    background = cv2.medianBlur(gray, 51)
    flat = cv2.divide(gray, background, scale=255)
    _, binary = cv2.threshold(flat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


# ------------------------------------------------------------------ OCR

def ocr_words(img):
    data = pytesseract.image_to_data(img, config="--oem 1 --psm 6", output_type=pytesseract.Output.DICT)
    words = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text:
            continue
        words.append({
            "text": text,
            "conf": float(data["conf"][i]),
            "x": data["left"][i], "y": data["top"][i], "w": data["width"][i], "h": data["height"][i],
            "line": (data["block_num"][i], data["par_num"][i], data["line_num"][i]),
        })
    return words


def group_lines(words):
    lines = {}
    for w in words:
        lines.setdefault(w["line"], []).append(w)
    ordered = [sorted(ws, key=lambda w: w["x"]) for ws in lines.values()]
    return sorted(ordered, key=lambda ws: min(w["y"] for w in ws))


def clean_token(text):
    return text.strip("|[](){}.,:;'\"!_-—–")


def read_digits(img, word, pad=12):
    """Second, independent reading of one mark: digits only, single line."""
    h, w = img.shape
    x0, y0 = max(0, word["x"] - pad), max(0, word["y"] - pad)
    x1, y1 = min(w, word["x"] + word["w"] + pad), min(h, word["y"] + word["h"] + pad)
    crop = cv2.copyMakeBorder(img[y0:y1, x0:x1], 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    data = pytesseract.image_to_data(crop, config="--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789",
                                     output_type=pytesseract.Output.DICT)
    texts = [(t.strip(), float(c)) for t, c in zip(data["text"], data["conf"]) if t.strip()]
    if len(texts) != 1:
        return None, 0.0
    return texts[0]


# ------------------------------------------------------------------ parsing

def _contains_keyword(text, keyword):
    return fuzz.partial_ratio(keyword.upper(), text.upper()) >= KEYWORD_MATCH_MIN


def _find_header(lines, template):
    """Locate the mark column from the header line.

    Returns ((left, centre) of the column title, header words). The title may be
    several words ("MARKS OBTAINED"); numbers can sit under its left edge or centre.
    """
    title_words = template["mark_column"].upper().split()
    keyword = template["mark_column_keyword"].upper()
    for ws in lines:
        line_text = " ".join(w["text"] for w in ws).upper()
        if "SUBJECT" not in line_text and fuzz.partial_ratio("SUBJECT", line_text) < KEYWORD_MATCH_MIN:
            continue
        for i, w in enumerate(ws):
            if fuzz.ratio(keyword, clean_token(w["text"]).upper()) < KEYWORD_MATCH_MIN:
                continue
            k = title_words.index(keyword)
            first = ws[max(0, i - k)]
            last = ws[min(len(ws) - 1, i + len(title_words) - 1 - k)]
            left, right = first["x"], last["x"] + last["w"]
            return (left, (left + right) / 2), ws
    return None, None


def _column_distance(word, column):
    left, centre = column
    return min(abs(word["x"] - left), abs(word["x"] + word["w"] / 2 - centre))


def _alias_table(template):
    table = {}
    for subject in template["subjects"]:
        for alias in subject["aliases"] + [subject["name"].upper()]:
            table[alias.upper()] = subject["name"]
    return table


def parse_lines(lines, template, img, header_x, header_line):
    aliases = _alias_table(template)
    max_marks = {s["name"]: s["max"] for s in template["subjects"]}
    marks = {}
    column_gap = 0.06 * img.shape[1]  # a number must sit within ~6 % of page width of the column

    for ws in lines:
        if ws is header_line:
            continue
        tokens = [(clean_token(w["text"]), w) for w in ws]
        tokens = [(t, w) for t, w in tokens if t]
        if template["has_subject_code"] and tokens and NUMBER_RE.match(tokens[0][0]):
            tokens = tokens[1:]  # leading subject code
        numeric = [(t, w) for t, w in tokens if NUMBER_RE.match(t)]
        # The subject name is the words before the first number. Anything after the
        # marks (grades such as "C1", often misread as "Cl") is ignored.
        words = []
        for t, _ in tokens:
            if NUMBER_RE.match(t):
                break
            words.append(t)
        name_text = " ".join(words).upper()
        if not name_text or not numeric:
            continue
        match = process.extractOne(name_text, aliases.keys(), scorer=fuzz.ratio,
                                   score_cutoff=SUBJECT_MATCH_MIN)
        if not match:
            continue
        subject = aliases[match[0]]

        # Pick the number sitting under the mark column header.
        candidates = sorted(numeric, key=lambda tw: _column_distance(tw[1], header_x))
        token, word = candidates[0]
        if _column_distance(word, header_x) > column_gap:
            marks[subject] = ReadMark(subject, None, 0.0, " ".join(t for t, _ in tokens),
                                      "no number found under the mark column")
            continue

        digits, digit_conf = read_digits(img, word)
        first = int(token)
        reading = ReadMark(subject, first, min(word["conf"], digit_conf), token)
        if digits is None or int(digits) != first:
            # Fail-safe: two independent readings disagree → not trusted.
            reading.confidence = 0.0
            reading.note = f"two readings disagree ({token} vs {digits or 'nothing'})"
        elif first > max_marks[subject]:
            reading.confidence = 0.0
            reading.note = f"{first} is above the maximum of {max_marks[subject]}"
        if subject in marks:
            # Same subject twice on one sheet is ambiguous: keep neither value.
            marks[subject] = ReadMark(subject, None, 0.0, token, "subject appears more than once")
            continue
        marks[subject] = reading
    return marks


def read_marksheet(data, template):
    import time

    started = time.perf_counter()
    result = SheetReading()
    img = preprocess(load_image(data))
    lines = group_lines(ocr_words(img))
    full_text = " ".join(w["text"] for ws in lines for w in ws)

    result.title_found = any(_contains_keyword(full_text, k) for k in template["identify_keywords"])
    header_x, header_line = _find_header(lines, template)
    result.header_found = header_x is not None

    if result.header_found:
        result.marks = parse_lines(lines, template, img, header_x, header_line)

    found = sum(1 for m in result.marks.values() if m.value is not None)
    if not result.title_found:
        result.reason = f"This doesn't look like a {template['short_label']} mark sheet (title not found)."
    elif not result.header_found:
        result.reason = f"The marks table header ('{template['mark_column']}') was not found."
    elif found < template["min_subjects"]:
        result.reason = (f"Only {found} subject marks could be read; at least "
                         f"{template['min_subjects']} are expected.")
    else:
        result.layout_ok = True
    result.seconds = time.perf_counter() - started
    return result
