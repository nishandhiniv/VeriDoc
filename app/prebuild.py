"""Build-time seeding: python -m app.prebuild TARGET_DIR

Runs the real engine once while the Docker image is built: demo applications,
the synthetic dataset and the first accuracy run. At startup the app copies
TARGET_DIR into its empty data folder, so a host that resets its disk on every
wake-up (Render's free plan) is ready instantly instead of redoing minutes of OCR.

No user accounts are stored here: those are created at startup from the
environment, so passwords never end up inside the image.
"""
import shutil
import sys
from pathlib import Path

from .config import Config


def main(target):
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    cfg = type("PrebuildConfig", (Config,), {
        "DATA_DIR": target, "UPLOAD_DIR": target / "uploads",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{target / 'veridoc.sqlite'}",
        "SEED_DEMO": True, "SEED_DEMO_ASYNC": False, "SEED_EVALUATION": True,
    })
    from . import create_app
    from .models import EvaluationRun, User, db

    app = create_app(cfg)
    with app.app_context():
        User.query.delete()
        for run in EvaluationRun.query.all():
            run.started_by = "image build"
        db.session.commit()
        runs = [r.status for r in EvaluationRun.query.all()]
    if runs != ["done"]:
        sys.exit(f"Prebuild evaluation did not finish: {runs}")
    print(f"Prebuilt demo data in {target}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/app/seed-data")
