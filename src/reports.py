from datetime import datetime, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from extensions import db
from models import Pet, Report, ReportPet

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

MAX_LOCATION_LENGTH = 255

# Real-world UTC offsets range from UTC+14 (Kiribati) to UTC-12 (Baker/
# Howland Islands), i.e. tz_offset_minutes (UTC - local) from -840 to
# +720. Anything outside that is forged/corrupted input, not a real
# timezone — reject it before it ever reaches timedelta(), which raises
# an uncaught OverflowError on an absurd value.
MIN_TZ_OFFSET_MINUTES = -14 * 60
MAX_TZ_OFFSET_MINUTES = 12 * 60


def _get_owned_report_or_404(report_id):
    """Every report lookup is scoped to current_user.id, same as pets."""
    report = Report.query.filter_by(id=report_id, owner_id=current_user.id).first()
    if report is None:
        abort(404)
    return report


def _validate_report_form(form):
    errors = {}

    last_seen_location = form.get("last_seen_location", "").strip()
    last_seen_at_raw = form.get("last_seen_at", "").strip()
    tz_offset_raw = form.get("tz_offset_minutes", "").strip()
    notes = form.get("notes", "").strip()
    pet_ids_raw = form.getlist("pet_ids")

    if not last_seen_location:
        errors["last_seen_location"] = "Last seen location is required."
    elif len(last_seen_location) > MAX_LOCATION_LENGTH:
        errors["last_seen_location"] = (
            f"Location must be {MAX_LOCATION_LENGTH} characters or fewer."
        )

    # The <input type="datetime-local"> value is a naive wall-clock
    # timestamp in the browser's local timezone, with no offset attached.
    # A hidden field (set by JS via Date.getTimezoneOffset(), minutes to
    # ADD to local time to get UTC) lets us normalize it before comparing
    # against datetime.utcnow() or storing it — every other timestamp in
    # this app is UTC, and comparing a naive local value against UTC
    # directly accepts genuinely-future local times in timezones behind
    # UTC and rejects genuinely-past ones in timezones ahead of it.
    try:
        tz_offset_minutes = int(tz_offset_raw) if tz_offset_raw else 0
    except ValueError:
        tz_offset_minutes = 0

    last_seen_at = None
    if last_seen_at_raw:
        if not (MIN_TZ_OFFSET_MINUTES <= tz_offset_minutes <= MAX_TZ_OFFSET_MINUTES):
            errors["last_seen_at"] = "Enter a valid date and time."
        else:
            try:
                local_dt = datetime.strptime(last_seen_at_raw, "%Y-%m-%dT%H:%M")
                last_seen_at = local_dt + timedelta(minutes=tz_offset_minutes)
                if last_seen_at > datetime.utcnow():
                    errors["last_seen_at"] = "Last seen time cannot be in the future."
            except ValueError:
                errors["last_seen_at"] = "Enter a valid date and time."

    # Only ever accept pet ids that are both well-formed and actually owned
    # by the current user — a forged id for another user's pet is silently
    # dropped rather than trusted.
    try:
        requested_ids = {int(pid) for pid in pet_ids_raw}
    except ValueError:
        requested_ids = set()

    owned_pets = []
    if requested_ids:
        owned_pets = Pet.query.filter(
            Pet.id.in_(requested_ids), Pet.owner_id == current_user.id
        ).all()

    if not owned_pets:
        errors["pet_ids"] = "Select at least one pet."

    cleaned = {
        "last_seen_location": last_seen_location,
        "last_seen_at": last_seen_at,
        "notes": notes or None,
        "pets": owned_pets,
    }
    return errors, cleaned


@reports_bp.route("", methods=["GET"])
@login_required
def list_reports():
    reports = (
        Report.query.filter_by(owner_id=current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return render_template("reports/list.html", reports=reports)


@reports_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_report():
    pets = Pet.query.filter_by(owner_id=current_user.id).order_by(Pet.name.asc()).all()

    if not pets:
        flash("Add a pet before filing a missing pet report.", "info")
        return redirect(url_for("pets.new_pet"))

    errors = {}
    values = {"last_seen_location": "", "last_seen_at": "", "notes": ""}
    selected_pet_ids = set()

    if request.method == "POST":
        errors, cleaned = _validate_report_form(request.form)
        values.update(request.form)
        selected_pet_ids = {p.id for p in cleaned["pets"]}

        if not errors:
            report = Report(
                owner_id=current_user.id,
                status="open",
                last_seen_location=cleaned["last_seen_location"],
                last_seen_at=cleaned["last_seen_at"],
                notes=cleaned["notes"],
            )
            db.session.add(report)
            db.session.flush()  # assigns report.id before the join rows

            for pet in cleaned["pets"]:
                db.session.add(ReportPet(report_id=report.id, pet_id=pet.id))

            db.session.commit()
            flash("Missing pet report filed.", "success")
            return redirect(url_for("reports.view_report", report_id=report.id))

    return render_template(
        "reports/form.html",
        errors=errors,
        values=values,
        pets=pets,
        selected_pet_ids=selected_pet_ids,
        form_action=url_for("reports.new_report"),
    )


@reports_bp.route("/<int:report_id>", methods=["GET"])
@login_required
def view_report(report_id):
    report = _get_owned_report_or_404(report_id)
    return render_template("reports/detail.html", report=report)
