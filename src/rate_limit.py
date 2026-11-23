"""Database-backed request limits for login and password reset (NF14)."""

import hashlib
from datetime import datetime, timedelta

from flask import current_app

from extensions import db

_SETTINGS = {
    "login": ("LOGIN_LIMIT", "LOGIN_WINDOW_SECONDS"),
    "reset": ("RESET_LIMIT", "RESET_WINDOW_SECONDS"),
}


class AuthAttempt(db.Model):
    __tablename__ = "auth_attempts"

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(20), nullable=False)
    key_hash = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )


def key_hash(email, address):
    """Email and client address are stored only as this SHA-256 digest."""
    raw = f"{(email or '').strip().lower()}\0{address or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cutoff(scope):
    seconds = current_app.config[_SETTINGS[scope][1]]
    return datetime.utcnow() - timedelta(seconds=seconds)


def is_limited(scope, email, address):
    """True once this email + address has used its attempts in the window."""
    used = AuthAttempt.query.filter(
        AuthAttempt.scope == scope,
        AuthAttempt.key_hash == key_hash(email, address),
        AuthAttempt.created_at > _cutoff(scope),
    ).count()
    return used >= current_app.config[_SETTINGS[scope][0]]


def record_attempt(scope, email, address):
    """Save one attempt and drop this scope's rows that left the window."""
    AuthAttempt.query.filter(
        AuthAttempt.scope == scope, AuthAttempt.created_at <= _cutoff(scope)
    ).delete(synchronize_session=False)
    db.session.add(AuthAttempt(scope=scope, key_hash=key_hash(email, address)))
    db.session.commit()


def reserve_attempt(scope, email, address):
    """Claim one attempt before doing the work; False means the limit is used.

    The row is committed before counting, so concurrent requests see each other
    and cannot all pass. A refused request removes its row, so blocked retries
    do not extend the window.
    """
    hashed = key_hash(email, address)
    cutoff = _cutoff(scope)
    AuthAttempt.query.filter(
        AuthAttempt.scope == scope, AuthAttempt.created_at <= cutoff
    ).delete(synchronize_session=False)
    attempt = AuthAttempt(scope=scope, key_hash=hashed)
    db.session.add(attempt)
    db.session.flush()
    # Read now: a concurrent clear_attempts may delete the row after the commit.
    attempt_id = attempt.id
    db.session.commit()

    used = AuthAttempt.query.filter(
        AuthAttempt.scope == scope,
        AuthAttempt.key_hash == hashed,
        AuthAttempt.created_at > cutoff,
    ).count()
    allowed = used <= current_app.config[_SETTINGS[scope][0]]
    if not allowed:
        AuthAttempt.query.filter_by(id=attempt_id).delete(synchronize_session=False)
    db.session.commit()
    return allowed


def clear_attempts(scope, email, address):
    AuthAttempt.query.filter_by(
        scope=scope, key_hash=key_hash(email, address)
    ).delete(synchronize_session=False)
    db.session.commit()
