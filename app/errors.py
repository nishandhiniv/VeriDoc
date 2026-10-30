import logging

from flask import render_template

from .models import db

log = logging.getLogger(__name__)

PAGES = {
    403: ("You don't have access to this page", "Your account can't open this page. If you need it, ask an admin."),
    404: ("Page not found", "The address may be mistyped, or the page has moved."),
    413: ("File too large", "The upload is bigger than the server accepts. Choose a smaller file and try again."),
    500: ("Something went wrong on our side", "The error has been logged. Try again, or go back to the start."),
}


def register(app):
    def render(code):
        title, message = PAGES[code]
        return render_template("errors/error.html", code=code, title=title, message=message), code

    for code in (403, 404, 413):
        app.register_error_handler(code, lambda e, code=code: render(code))

    @app.errorhandler(500)
    def server_error(e):
        # NFR-14: log details, never show a stack trace.
        log.exception("Unhandled error: %s", getattr(e, "original_exception", e))
        db.session.rollback()
        return render(500)
