import json
from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "reviewer" | "admin"
    password_hash = db.Column(db.String(255), nullable=False)

    __table_args__ = (db.CheckConstraint("role IN ('reviewer', 'admin')", name="ck_user_role"),)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


# Automatic outcomes. The system never rejects on its own (FR-R01).
AUTO_CLEARED = "auto_cleared"
NEEDS_REVIEW = "needs_review"

DECISIONS = {"approve": "Approved", "reject": "Rejected", "reupload": "Re-upload requested"}


class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    contact = db.Column(db.String(120), nullable=False)
    board = db.Column(db.String(20), nullable=False)  # template id, e.g. "tn_hsc"
    register_number = db.Column(db.String(30), nullable=False)
    marksheet_file = db.Column(db.String(255), nullable=False)
    photo_file = db.Column(db.String(255), nullable=False)
    marksheet_original_name = db.Column(db.String(255))
    photo_original_name = db.Column(db.String(255))
    auto_status = db.Column(db.String(20))  # AUTO_CLEARED | NEEDS_REVIEW, set by validation
    issue_count = db.Column(db.Integer, default=0)
    decision = db.Column(db.String(20))  # latest human decision, see Decision for history
    is_demo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    validated_at = db.Column(db.DateTime)

    marks = db.relationship("EnteredMark", backref="application", cascade="all, delete-orphan",
                            order_by="EnteredMark.position")
    checks = db.relationship("CheckResult", backref="application", cascade="all, delete-orphan",
                             order_by="CheckResult.position")
    decisions = db.relationship("Decision", backref="application", cascade="all, delete-orphan",
                                order_by="Decision.created_at")

    __table_args__ = (
        db.CheckConstraint(f"auto_status IS NULL OR auto_status IN ('{AUTO_CLEARED}', '{NEEDS_REVIEW}')",
                           name="ck_app_auto_status"),
        db.CheckConstraint("decision IS NULL OR decision IN ('approve', 'reject', 'reupload')",
                           name="ck_app_decision"),
    )

    @property
    def queue_state(self):
        if self.decision:
            return "decided"
        return self.auto_status or NEEDS_REVIEW


class EnteredMark(db.Model):
    __tablename__ = "entered_marks"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    mark = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("application_id", "subject", name="uq_mark_subject"),
                      db.CheckConstraint("mark >= 0", name="ck_mark_non_negative"))


class CheckResult(db.Model):
    """One row of the validation report (FR-R02, FR-R03)."""

    __tablename__ = "check_results"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    section = db.Column(db.String(20), nullable=False)  # "marks" | "marksheet" | "photo" | "system"
    name = db.Column(db.String(80), nullable=False)
    result = db.Column(db.String(20), nullable=False)
    entered = db.Column(db.String(80))
    uploaded = db.Column(db.String(80))
    detail = db.Column(db.String(255))
    rule = db.Column(db.String(255))
    confidence = db.Column(db.Float)
    position = db.Column(db.Integer, default=0)
    is_issue = db.Column(db.Boolean, default=False)


class Decision(db.Model):
    """Append-only audit trail of reviewer decisions (FR-Q04)."""

    __tablename__ = "decisions"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    reviewer = db.relationship("User")

    __table_args__ = (db.CheckConstraint("decision IN ('approve', 'reject', 'reupload')",
                                         name="ck_decision_value"),)


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value_json = db.Column(db.Text, nullable=False)

    @property
    def value(self):
        return json.loads(self.value_json)


class EvaluationRun(db.Model):
    __tablename__ = "evaluation_runs"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="running")  # running | done | failed
    started_by = db.Column(db.String(120))
    report_json = db.Column(db.Text)

    __table_args__ = (db.CheckConstraint("status IN ('running', 'done', 'failed')", name="ck_eval_status"),)

    @property
    def report(self):
        return json.loads(self.report_json) if self.report_json else None
