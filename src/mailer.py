"""Outgoing mail. MAIL_BACKEND selects console, memory, or smtp."""

import smtplib
from email.message import EmailMessage

from flask import current_app


def _send_smtp(to, subject, body):
    config = current_app.config
    message = EmailMessage()
    message["From"] = config["MAIL_FROM"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(config["MAIL_HOST"], config["MAIL_PORT"], timeout=10) as server:
        if config["MAIL_USE_TLS"]:
            server.starttls()
        if config["MAIL_USERNAME"]:
            server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        server.send_message(message)


def send_email(to, subject, body):
    """Send one message. Raises on failure so the caller can decide what the
    user sees; callers must not log the body, which may hold a reset link."""
    backend = current_app.config.get("MAIL_BACKEND", "console")
    if backend == "console":
        if not (current_app.debug or current_app.testing):
            current_app.logger.error(
                "Console mail is disabled outside debug and testing."
            )
            raise RuntimeError("Console mail backend is disabled.")
        print(f"To: {to}\nSubject: {subject}\n\n{body}\n", flush=True)
    elif backend == "memory":
        current_app.extensions.setdefault("mail_outbox", []).append(
            {"to": to, "subject": subject, "body": body}
        )
    elif backend == "smtp":
        _send_smtp(to, subject, body)
    else:
        raise ValueError("Unknown MAIL_BACKEND.")
