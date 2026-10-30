"""Mark sheet template profiles (FR-V03, A2a): one JSON file per board/exam."""
import json
from functools import lru_cache
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "templates"


@lru_cache(maxsize=None)
def all_templates():
    templates = {}
    for path in sorted(TEMPLATE_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        templates[data["id"]] = data
    return templates


def get_template(template_id):
    return all_templates().get(template_id)


def subject_names(template_id):
    return [s["name"] for s in get_template(template_id)["subjects"]]


def subject_max(template_id, name):
    for s in get_template(template_id)["subjects"]:
        if s["name"] == name:
            return s["max"]
    return None
