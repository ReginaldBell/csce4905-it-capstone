import hashlib
import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import unquote, urlsplit

from flask import (
    Blueprint,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

import mailer
from extensions import db
from models import PasswordResetToken, Pet, User
from rate_limit import clear_attempts, reserve_attempt

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL_LENGTH = 255
MIN_PASSWORD_LENGTH = 8
STALE_PET_DAYS = 90
TOO_MANY_ATTEMPTS = "Too many attempts. Try again later."
RESET_SENT_MESSAGE = "If an account exists for that email, we sent a reset link."
RESET_INVALID_MESSAGE = "This reset link is invalid or has expired."


def _flash_stale_pet_reminder(user):
    """Nudge at login if any of the user's pets haven't been updated in
    STALE_PET_DAYS — the info or photo may be out of date."""
    cutoff = datetime.utcnow() - timedelta(days=STALE_PET_DAYS)
    stale_pets = (
        Pet.query.filter(Pet.owner_id == user.id, Pet.updated_at < cutoff)
        .order_by(Pet.name.asc())
        .all()
    )
    if not stale_pets:
        return

    names = ", ".join(pet.name for pet in stale_pets)
    pet_word = "pet" if len(stale_pets) == 1 else "pets"
    flash(
        f"It's been {STALE_PET_DAYS}+ days since the following {pet_word} had "
        f"an update: {names}. Take a moment to confirm the info and photo are "
        "still current.",
        "info",
    )


def _password_errors(password, confirm_password):
    """Shared by registration and password reset."""
    errors = {}
    if not password:
        errors["password"] = "Password is required."
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = (
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    if password and confirm_password != password:
        errors["confirm_password"] = "Passwords do not match."
    return errors


def _safe_next_url(target):
    """Accept only a same-site relative path. Encoded forms are checked too,
    so "/%2F/host" or "/%5Chost" can't turn into an off-site redirect."""
    if not target:
        return None
    for candidate in (target, unquote(target)):
        if not candidate.startswith("/") or candidate.startswith("//"):
            return None
        if "\\" in candidate or any(
            ord(char) < 32 or ord(char) == 127 for char in candidate
        ):
            return None
    try:
        parts = urlsplit(target)
    except ValueError:
        return None
    if parts.scheme or parts.netloc:
        return None
    return target


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invalidate_reset_tokens(user_id):
    """Mark every unused reset link for this user as spent. Does not commit."""
    PasswordResetToken.query.filter_by(user_id=user_id, used_at=None).update(
        {"used_at": datetime.utcnow()}, synchronize_session=False
    )


def _issue_reset_token(user):
    invalidate_reset_tokens(user.id)
    token = secrets.token_urlsafe(32)
    minutes = current_app.config["PASSWORD_RESET_TTL_MINUTES"]
    db.session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=datetime.utcnow() + timedelta(minutes=minutes),
        )
    )
    db.session.commit()
    return token


def _can_build_reset_link():
    """Without APP_BASE_URL the link would trust the request's Host header, so
    allow that only for local mail that never leaves the machine."""
    if current_app.config.get("APP_BASE_URL"):
        return True
    local_mail = current_app.config.get("MAIL_BACKEND") in ("console", "memory")
    return bool((current_app.debug or current_app.testing) and local_mail)


def _reset_link(token):
    # A configured base URL keeps a forged Host header out of the emailed link.
    base_url = current_app.config.get("APP_BASE_URL")
    if base_url:
        path = url_for("auth.reset_password", token=token)
        return f"{base_url.rstrip('/')}{path}"
    return url_for("auth.reset_password", token=token, _external=True)


def _send_reset_email(user, token):
    minutes = current_app.config["PASSWORD_RESET_TTL_MINUTES"]
    body = (
        "We received a request to reset your Pet Finder password.\n\n"
        f"Open this link within {minutes} minutes to choose a new password:\n"
        f"{_reset_link(token)}\n\n"
        "If you did not ask for this, you can ignore this email."
    )
    try:
        mailer.send_email_background(
            user.email, "Reset your Pet Finder password", body
        )
    except Exception as error:  # Any mail failure must look the same to the user.
        # Only the error type: its text could echo the message with the token.
        current_app.logger.error(
            "Password reset email failed: %s", type(error).__name__
        )


def _process_reset_request(email):
    """Every outcome renders the same page, so nothing here reveals whether
    the account exists or the limit was reached."""
    if not reserve_attempt("reset", email, request.remote_addr):
        return
    user = User.query.filter_by(email=email).first()
    if user is None:
        return
    if not _can_build_reset_link():
        current_app.logger.error("Password reset skipped: APP_BASE_URL is not set.")
        return
    _send_reset_email(user, _issue_reset_token(user))


def _valid_reset_token(token):
    record = PasswordResetToken.query.filter_by(token_hash=_hash_token(token)).first()
    if record is None or record.used_at is not None:
        return None
    if record.expires_at <= datetime.utcnow():
        return None
    return record


def _claim_reset_token(record):
    """Atomically mark the token used, so two submits can't both succeed."""
    claimed = PasswordResetToken.query.filter_by(id=record.id, used_at=None).update(
        {"used_at": datetime.utcnow()}, synchronize_session=False
    )
    return claimed == 1


def _reset_page(status=200, **context):
    response = make_response(
        render_template("auth/reset_password.html", **context), status
    )
    # The URL holds the token: keep it out of caches and Referer headers.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _invalid_reset_page():
    return _reset_page(400, invalid_message=RESET_INVALID_MESSAGE, errors={})


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pets.list_pets"))

    errors = {}
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email:
            errors["email"] = "Email is required."
        elif len(email) > MAX_EMAIL_LENGTH:
            errors["email"] = f"Email must be {MAX_EMAIL_LENGTH} characters or fewer."
        elif not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        elif User.query.filter_by(email=email).first() is not None:
            errors["email"] = "An account with this email already exists."

        errors.update(_password_errors(password, confirm_password))

        if not errors:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created.", "success")
            return redirect(url_for("pets.list_pets"))

    return render_template("auth/register.html", errors=errors, email=email)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pets.list_pets"))

    errors = {}
    email = ""
    status = 200

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        address = request.remote_addr

        if not reserve_attempt("login", email, address):
            errors["form"] = TOO_MANY_ATTEMPTS
            status = 429
        else:
            user = User.query.filter_by(email=email).first()
            if user is None or not user.check_password(password):
                errors["form"] = "Invalid email or password."
            else:
                clear_attempts("login", email, address)
                login_user(user)
                flash("Logged in.", "success")
                _flash_stale_pet_reminder(user)
                next_url = _safe_next_url(request.args.get("next"))
                return redirect(next_url or url_for("pets.list_pets"))

    return render_template("auth/login.html", errors=errors, email=email), status


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    errors = {}
    email = ""
    message = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            errors["email"] = "Email is required."
        elif len(email) > MAX_EMAIL_LENGTH or not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        else:
            _process_reset_request(email)
            message = RESET_SENT_MESSAGE
            email = ""

    return render_template(
        "auth/forgot_password.html", errors=errors, email=email, message=message
    )


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    record = _valid_reset_token(token)
    if record is None:
        return _invalid_reset_page()

    errors = {}
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        errors = _password_errors(password, confirm_password)

        if not errors:
            if not _claim_reset_token(record):
                db.session.rollback()
                return _invalid_reset_page()
            user = db.session.get(User, record.user_id)
            user.set_password(password)
            user.session_version = User.session_version + 1  # Ends older sessions.
            invalidate_reset_tokens(user.id)
            db.session.commit()
            # A lockout from forgotten-password guesses shouldn't outlive the fix.
            clear_attempts("login", user.email, request.remote_addr)
            if current_user.is_authenticated:
                logout_user()
            flash("Your password was updated. Log in with it now.", "success")
            return redirect(url_for("auth.login"))

    return _reset_page(errors=errors, invalid_message=None)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
