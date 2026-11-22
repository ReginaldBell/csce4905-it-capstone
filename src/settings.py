"""Account settings. Display preferences are stored by the browser."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from community import RADIUS_CHOICES, _name_error
from extensions import db

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("", methods=["GET", "POST"])
@login_required
def view_settings():
    display_name = current_user.display_name or ""
    errors = {}
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        name_error = _name_error(display_name)
        if name_error:
            errors["display_name"] = name_error
        else:
            current_user.display_name = display_name
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("settings.view_settings"))
    return render_template(
        "settings/index.html",
        display_name=display_name,
        errors=errors,
        radii=RADIUS_CHOICES,
    )
