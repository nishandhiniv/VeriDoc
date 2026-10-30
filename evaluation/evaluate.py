"""Accuracy evaluation (US-12, FR-E05/E06).

Runs the real engine over the labelled synthetic dataset and compares every
result with the ground truth written by the generator. Nothing is estimated:
every figure is a count from this run.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from engine.marksheet import read_marksheet
from engine.photo import check_photo
from engine.templates_registry import get_template
from engine.validate import mark_checks

PHOTO_RULE_KEYS = {"File format": "format", "File size": "file_size", "Resolution": "min_resolution",
                   "Maximum dimensions": "max_dimensions", "Aspect ratio": "aspect_ratio",
                   "Orientation": "orientation", "Brightness": "brightness", "Sharpness": "sharpness"}


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def evaluate_marksheets(dataset_dir, settings, errors):
    threshold = settings["ocr_confidence_min"]
    truth = json.loads((dataset_dir / "ground_truth.json").read_text())
    groups = {}
    outcome = {"agree": 0, "total": 0, "problems": 0, "problems_flagged": 0, "flagged": 0,
               "flagged_true": 0, "false_match": 0}
    apps = {"total": 0, "to_review": 0, "clean_total": 0, "clean_to_review": 0,
            "planted_total": 0, "planted_to_review": 0}

    for rec in truth["marksheets"]:
        template = get_template(rec["template"])
        key = f"{template['short_label']} · {rec['variant']}"
        g = groups.setdefault(key, {"template": template["short_label"], "variant": rec["variant"],
                                    "sheets": 0, "fields": 0, "correct": 0, "untrusted": 0, "wrong": 0,
                                    "layout_failed": 0})
        g["sheets"] += 1
        sheet = read_marksheet((dataset_dir / rec["file"]).read_bytes(), template)
        if not sheet.layout_ok:
            g["layout_failed"] += 1

        # (a) Extraction accuracy, field by field.
        for subject, true_mark in rec["sheet_marks"].items():
            g["fields"] += 1
            read = sheet.marks.get(subject)
            trusted = read is not None and read.value is not None and read.confidence >= threshold
            if trusted and read.value == true_mark:
                g["correct"] += 1
            elif trusted:
                g["wrong"] += 1
                errors.append({"file": rec["file"], "field": f"{subject} (extracted mark)",
                               "expected": true_mark, "got": read.value,
                               "note": "WRONG VALUE TRUSTED by OCR"})
            else:
                g["untrusted"] += 1
                errors.append({"file": rec["file"], "field": f"{subject} (extracted mark)",
                               "expected": true_mark, "got": None if read is None else read.value,
                               "note": "not read with confidence; sent to review" if read else "subject not found"})

        # (b) Entered vs. uploaded outcomes, against the planted errors.
        checks = mark_checks(rec["entered_marks"], sheet, template, settings)
        got = {c.name: c.result for c in checks if c.section == "marks"}
        for subject, expected in rec["expected"].items():
            result = got.get(subject)
            outcome["total"] += 1
            outcome["agree"] += result == expected
            is_problem = expected != "match"
            flagged = result != "match"
            outcome["problems"] += is_problem
            outcome["problems_flagged"] += is_problem and flagged
            outcome["flagged"] += flagged
            outcome["flagged_true"] += flagged and is_problem
            if is_problem and result == "match":
                outcome["false_match"] += 1
                errors.append({"file": rec["file"], "field": f"{subject} (outcome)", "expected": expected,
                               "got": result, "note": "FALSE MATCH: fail-safe broken"})
            elif result != expected:
                errors.append({"file": rec["file"], "field": f"{subject} (outcome)", "expected": expected,
                               "got": result, "note": "sent to review" if flagged else ""})

        to_review = any(c.is_issue for c in checks)
        apps["total"] += 1
        apps["to_review"] += to_review
        if rec["planted_error"]:
            apps["planted_total"] += 1
            apps["planted_to_review"] += to_review
        else:
            apps["clean_total"] += 1
            apps["clean_to_review"] += to_review

    for g in groups.values():
        g["accuracy"] = pct(g["correct"], g["fields"])
    return {
        "sheets": len(truth["marksheets"]),
        "groups": sorted(groups.values(), key=lambda g: (g["template"], g["variant"] != "clean")),
        "clean_accuracy": pct(sum(g["correct"] for g in groups.values() if g["variant"] == "clean"),
                              sum(g["fields"] for g in groups.values() if g["variant"] == "clean")),
        "degraded_accuracy": pct(sum(g["correct"] for g in groups.values() if g["variant"] == "degraded"),
                                 sum(g["fields"] for g in groups.values() if g["variant"] == "degraded")),
        "wrong_trusted": sum(g["wrong"] for g in groups.values()),
        "outcomes": {**outcome, "agreement": pct(outcome["agree"], outcome["total"]),
                     "recall": pct(outcome["problems_flagged"], outcome["problems"]),
                     "precision": pct(outcome["flagged_true"], outcome["flagged"])},
        "applications": {**apps, "to_review_pct": pct(apps["to_review"], apps["total"]),
                         "clean_to_review_pct": pct(apps["clean_to_review"], apps["clean_total"]),
                         "planted_to_review_pct": pct(apps["planted_to_review"], apps["planted_total"])},
    }


def evaluate_photos(dataset_dir, settings, errors):
    truth = json.loads((dataset_dir / "ground_truth.json").read_text())
    rules = {key: {"rule": name, "total": 0, "agree": 0} for name, key in PHOTO_RULE_KEYS.items()}
    for rec in truth["photos"]:
        got = {PHOTO_RULE_KEYS[c.name]: c for c in check_photo((dataset_dir / rec["file"]).read_bytes(), settings)
               if c.name in PHOTO_RULE_KEYS}
        for key, expected in rec["expected"].items():
            check = got.get(key)
            result = check.result if check else "error"
            rules[key]["total"] += 1
            if result == expected:
                rules[key]["agree"] += 1
            else:
                errors.append({"file": rec["file"], "field": f"photo: {rules[key]['rule']}",
                               "expected": expected, "got": result, "note": check.detail if check else ""})
    for r in rules.values():
        r["accuracy"] = pct(r["agree"], r["total"])
    return {"photos": len(truth["photos"]), "rules": list(rules.values()),
            "overall": pct(sum(r["agree"] for r in rules.values()), sum(r["total"] for r in rules.values()))}


def run_evaluation(dataset_dir, settings):
    dataset_dir = Path(dataset_dir)
    started = time.perf_counter()
    errors = []
    marks = evaluate_marksheets(dataset_dir, settings, errors)
    photos = evaluate_photos(dataset_dir, settings, errors)
    return {
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "dataset": {"marksheets": marks["sheets"], "photos": photos["photos"],
                    "seed": json.loads((dataset_dir / "ground_truth.json").read_text())["seed"]},
        "settings": {"ocr_confidence_min": settings["ocr_confidence_min"],
                     "mark_tolerance": settings["mark_tolerance"]},
        "marks": marks,
        "photos": photos,
        "false_match": marks["outcomes"]["false_match"],
        "errors": errors,
        "seconds": round(time.perf_counter() - started, 1),
    }


def to_markdown(report):
    m, p = report["marks"], report["photos"]
    lines = [
        f"# VeriDoc accuracy report",
        f"Measured on synthetic data, {report['run_at']}, n = {report['dataset']['marksheets']} mark sheets "
        f"+ {report['dataset']['photos']} photos (seed {report['dataset']['seed']}).",
        "",
        f"- **False matches (fail-safe gate): {report['false_match']}**",
        f"- Mark extraction accuracy, clean: {m['clean_accuracy']} % · degraded: {m['degraded_accuracy']} %",
        f"- Wrong values trusted by OCR: {m['wrong_trusted']}",
        f"- Planted-error detection recall: {m['outcomes']['recall']} % · precision: {m['outcomes']['precision']} %",
        f"- Applications with planted errors sent to review: {m['applications']['planted_to_review_pct']} %",
        f"- Correct applications sent to review (false alarms): {m['applications']['clean_to_review_pct']} %",
        f"- Photo rule agreement: {p['overall']} %",
        "",
        "| Template · variant | Sheets | Fields | Correct | Untrusted (review) | Wrong but trusted | Accuracy |",
        "|---|---|---|---|---|---|---|",
    ]
    for g in m["groups"]:
        lines.append(f"| {g['template']} · {g['variant']} | {g['sheets']} | {g['fields']} | {g['correct']} | "
                     f"{g['untrusted']} | {g['wrong']} | {g['accuracy']} % |")
    lines += ["", "| Photo rule | Photos | Agree | Accuracy |", "|---|---|---|---|"]
    for r in p["rules"]:
        lines.append(f"| {r['rule']} | {r['total']} | {r['agree']} | {r['accuracy']} % |")
    lines += ["", f"Errors listed: {len(report['errors'])}"]
    for e in report["errors"]:
        lines.append(f"- {e['file']} · {e['field']}: expected {e['expected']}, got {e['got']} {e['note']}")
    return "\n".join(lines) + "\n"
