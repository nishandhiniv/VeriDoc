"""Reviewer and admin pages (US-08, US-09, US-10)."""
from functools import wraps
from urllib.parse import urlsplit

from flask import (Blueprint, abort, flash, make_response, redirect, render_template, request, send_file,
                   url_for)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from engine.templates_registry import all_templates

from .models import AUTO_CLEARED, DECISIONS, NEEDS_REVIEW, Application, Decision, User, db
from .services import upload_path

bp = Blueprint("staff", __name__, url_prefix="/staff")

QUEUE_TABS = [("needs_review", "Needs review"), ("auto_cleared", "Auto-cleared"), ("decided", "Decided")]


def admin_required(view):
    """Server-side role check (FR-S02): reviewers get 403, not just a hidden link."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.after_request
def no_store(response):
    # Protected pages must not reappear from the browser cache after sign-out (US-09 AC5).
    response.headers["Cache-Control"] = "no-store"
    return response


# ------------------------------------------------------------------ US-09

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("staff.queue"))
    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            target = request.args.get("next", "")
            # Only allow relative, same-site redirects.
            if not target or urlsplit(target).netloc or not target.startswith("/"):
                target = url_for("staff.queue")
            return redirect(target)
        error = "Email or password is incorrect."
    return render_template("staff/login.html", error=error, email=email), (401 if error else 200)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You've signed out.", "success")
    return redirect(url_for("staff.login"))


# ------------------------------------------------------------------ US-10

def queue_query(state):
    q = Application.query
    if state == "decided":
        return q.filter(Application.decision.isnot(None)).order_by(Application.created_at.desc())
    q = q.filter(Application.decision.is_(None))
    if state == "auto_cleared":
        return q.filter(Application.auto_status == AUTO_CLEARED).order_by(Application.created_at.asc())
    return q.filter(Application.auto_status != AUTO_CLEARED).order_by(Application.created_at.asc())


def queue_counts():
    undecided = Application.decision.is_(None)
    return {
        "needs_review": Application.query.filter(undecided, Application.auto_status != AUTO_CLEARED).count(),
        "auto_cleared": Application.query.filter(undecided, Application.auto_status == AUTO_CLEARED).count(),
        "decided": Application.query.filter(Application.decision.isnot(None)).count(),
    }


@bp.route("/")
@login_required
def queue():
    state = request.args.get("status", "needs_review")
    if state not in dict(QUEUE_TABS):
        state = "needs_review"
    return render_template("staff/queue.html", apps=queue_query(state).all(), state=state, tabs=QUEUE_TABS,
                           counts=queue_counts(), templates=all_templates(), decisions=DECISIONS)


# ------------------------------------------------------------------ US-08

@bp.route("/applications/<reference>")
@login_required
def report(reference):
    app = Application.query.filter_by(reference=reference).first_or_404()
    sections = {key: [c for c in app.checks if c.section == key] for key in ("marks", "marksheet", "photo", "system")}
    return render_template("staff/report.html", app=app, sections=sections, template=all_templates().get(app.board),
                           decisions=DECISIONS, errors={}, form={})


@bp.route("/applications/<reference>/file/<kind>")
@login_required
def application_file(reference, kind):
    app = Application.query.filter_by(reference=reference).first_or_404()
    if kind not in ("marksheet", "photo"):
        abort(404)
    name = app.marksheet_file if kind == "marksheet" else app.photo_file
    response = make_response(send_file(upload_path(name)))
    response.headers["Content-Disposition"] = "inline"
    return response


@bp.route("/applications/<reference>/decision", methods=["POST"])
@login_required
def decide(reference):
    app = Application.query.filter_by(reference=reference).first_or_404()
    decision = request.form.get("decision", "")
    comment = request.form.get("comment", "").strip()
    errors = {}
    if decision not in DECISIONS:
        errors["decision"] = "Choose Approve, Reject or Request re-upload."
    elif decision in ("reject", "reupload") and not comment:
        errors["comment"] = "Add a comment explaining what the applicant needs to know."
    if len(comment) > 2000:
        errors["comment"] = "Keep the comment under 2000 characters."
    if errors:
        sections = {key: [c for c in app.checks if c.section == key] for key in ("marks", "marksheet", "photo", "system")}
        return render_template("staff/report.html", app=app, sections=sections,
                               template=all_templates().get(app.board), decisions=DECISIONS, errors=errors,
                               form={"decision": decision, "comment": comment}), 400
    # Append-only audit trail (FR-Q04); the application keeps the latest decision.
    db.session.add(Decision(application=app, reviewer=current_user, decision=decision, comment=comment or None))
    app.decision = decision
    db.session.commit()
    flash(f"{app.reference}: {DECISIONS[decision]}.", "success")
    return redirect(url_for("staff.queue"))


# ------------------------------------------------------------------ US-12

@bp.route("/accuracy")
@admin_required
def accuracy():
    from .evaluation_runner import is_running
    from .models import EvaluationRun
    latest = EvaluationRun.query.filter_by(status="done").order_by(EvaluationRun.id.desc()).first()
    last = EvaluationRun.query.order_by(EvaluationRun.id.desc()).first()
    return render_template("staff/accuracy.html", run=latest, report=latest.report if latest else None,
                           running=is_running(), last_failed=last is not None and last.status == "failed")


@bp.route("/accuracy/run", methods=["POST"])
@admin_required
def run_accuracy():
    from flask import current_app
    from .evaluation_runner import start_evaluation
    run = start_evaluation(current_app._get_current_object(), current_user.email,
                           background=not current_app.config.get("TESTING"))
    if run is None:
        flash("An evaluation is already running.", "info")
    elif run.status == "running":
        flash("Evaluation started. It runs in the background; this page refreshes until it finishes.", "info")
    return redirect(url_for("staff.accuracy"))
