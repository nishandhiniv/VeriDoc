"""Runs the accuracy evaluation (US-12) in the background and stores the report."""
import json
import logging
import threading
from pathlib import Path

from dataset.generator import generate
from evaluation.evaluate import run_evaluation

from .models import EvaluationRun, db
from .settings_store import load_settings

log = logging.getLogger(__name__)
_lock = threading.Lock()


def dataset_dir(app):
    return Path(app.config["DATA_DIR"]) / "dataset"


def is_running():
    return EvaluationRun.query.filter_by(status="running").first() is not None


def _execute(app, run_id):
    with app.app_context():
        run = db.session.get(EvaluationRun, run_id)
        try:
            target = dataset_dir(app)
            if not (target / "ground_truth.json").exists():
                generate(target)
            report = run_evaluation(target, load_settings())
            run.report_json = json.dumps(report)
            run.status = "done"
        except Exception:  # noqa: BLE001
            log.exception("Evaluation failed")
            db.session.rollback()
            run = db.session.get(EvaluationRun, run_id)
            run.status = "failed"
        db.session.commit()


def start_evaluation(app, started_by, background=True):
    """Start a run unless one is already running. Returns the run, or None if busy."""
    with _lock:
        if is_running():
            return None
        run = EvaluationRun(status="running", started_by=started_by)
        db.session.add(run)
        db.session.commit()
        run_id = run.id
    if background:
        threading.Thread(target=_execute, args=(app, run_id), daemon=True, name="evaluation").start()
    else:
        _execute(app, run_id)
    return db.session.get(EvaluationRun, run_id)


def mark_interrupted_runs():
    """A restart kills background threads; don't leave runs stuck as 'running'."""
    for run in EvaluationRun.query.filter_by(status="running").all():
        run.status = "failed"
    db.session.commit()
