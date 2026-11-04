import re
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import Pet, User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
STALE_PET_DAYS = 90


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
        elif not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        elif User.query.filter_by(email=email).first() is not None:
            errors["email"] = "An account with this email already exists."

        if not password:
            errors["password"] = "Password is required."
        elif len(password) < MIN_PASSWORD_LENGTH:
            errors["password"] = (
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )

        if password and confirm_password != password:
            errors["confirm_password"] = "Passwords do not match."

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

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            errors["form"] = "Invalid email or password."
        else:
            login_user(user)
            flash("Logged in.", "success")
            _flash_stale_pet_reminder(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("pets.list_pets"))

    return render_template("auth/login.html", errors=errors, email=email)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
