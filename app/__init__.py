import logging
import shutil

from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from .config import Config
from .models import User, db

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "staff.login"
login_manager.login_message = "Sign in to continue."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = Flask(__name__)
    app.config.from_object(config_class)

    data_dir = app.config["DATA_DIR"]
    seed_from = app.config.get("PREBUILT_DATA_DIR")
    if seed_from and seed_from.exists() and not (data_dir / "veridoc.sqlite").exists():
        # Fresh disk: start from the data prepared when the image was built (app/prebuild.py).
        shutil.copytree(seed_from, data_dir, dirs_exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_DIR"].mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import errors, public, staff

    app.register_blueprint(public.bp)
    app.register_blueprint(staff.bp)
    errors.register(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    with app.app_context():
        db.create_all()
        from .seed import seed_all

        seed_all(app)

    return app
