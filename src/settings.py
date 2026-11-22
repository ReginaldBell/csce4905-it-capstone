"""Account settings. Display preferences are stored by the browser."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from auth import EMAIL_RE, MAX_EMAIL_LENGTH, invalidate_reset_tokens
from community import RADIUS_CHOICES, _name_error
from contacts import PHONE_RE
from extensions import db
from models import User

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

MAX_FULL_NAME_LENGTH = 100
EMAIL_TAKEN = "An account with this email already exists."


def _validate_account_form(form):
    """A field missing from the POST keeps its saved value."""
    errors = {}

    raw_display_name = form.get("display_name")
    if raw_display_name is None:
        display_name = current_user.display_name
    elif raw_display_name == "":
        display_name = None
    else:
        # Whitespace-only is a mistake, not a request to clear the name.
        display_name = raw_display_name.strip()
        name_error = _name_error(display_name)
        if name_error:
            errors["display_name"] = name_error

    full_name = form.get("full_name", current_user.full_name or "").strip()
    if len(full_name) > MAX_FULL_NAME_LENGTH:
        errors["full_name"] = (
            f"Full name must be {MAX_FULL_NAME_LENGTH} characters or fewer."
        )

    phone = form.get("phone", current_user.phone or "").strip()
    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Enter a valid phone number."

    raw_email = form.get("email")
    email = current_user.email if raw_email is None else raw_email.strip().lower()
    if raw_email is None:
        pass  # Omitted: never an email change, whatever the stored value looks like.
    elif not email:
        errors["email"] = "Email is required."
    elif len(email) > MAX_EMAIL_LENGTH or not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    elif email != current_user.email:
        # Password first, so this form can't be used to probe which emails exist.
        if not current_user.check_password(form.get("current_password", "")):
            errors["current_password"] = (
                "Enter your current password to change your email."
            )
        elif User.query.filter_by(email=email).first() is not None:
            errors["email"] = EMAIL_TAKEN

    cleaned = {
        "display_name": display_name,
        "full_name": full_name or None,
        "phone": phone or None,
        "email": email,
    }
    return errors, cleaned


@settings_bp.route("", methods=["GET", "POST"])
@login_required
def view_settings():
    values = {
        "display_name": current_user.display_name or "",
        "full_name": current_user.full_name or "",
        "phone": current_user.phone or "",
        "email": current_user.email,
    }
    errors = {}
    if request.method == "POST":
        errors, cleaned = _validate_account_form(request.form)
        for field in values:
            if field in request.form:
                values[field] = request.form[field].strip()

        if not errors:
            email_changed = cleaned["email"] != current_user.email
            user_id = current_user.id
            for field, value in cleaned.items():
                setattr(current_user, field, value)
            try:
                if email_changed:
                    # A link mailed to the old address must not outlive the change.
                    # This query autoflushes, so it can raise on a concurrent signup.
                    invalidate_reset_tokens(user_id)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["email"] = EMAIL_TAKEN
            else:
                flash("Profile updated.", "success")
                return redirect(url_for("settings.view_settings"))
    return render_template(
        "settings/index.html",
        values=values,
        errors=errors,
        radii=RADIUS_CHOICES,
    )
