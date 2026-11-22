import os
import re
import uuid
from datetime import date, datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import Pet, format_measure

pets_bp = Blueprint("pets", __name__, url_prefix="/pets")

SPECIES_CHOICES = ["Dog", "Cat", "Bird", "Rabbit", "Other"]
MAX_NAME_LENGTH = 100
MAX_HEIGHT_INCHES = 120
MAX_WEIGHT_LBS = 500
MAX_COLORS_LENGTH = 100
MAX_MARKINGS_LENGTH = 255
SEX_VALUES = {value for value, _label in Pet.SEX_CHOICES}
MICROCHIP_VALUES = {value for value, _label in Pet.MICROCHIP_CHOICES}
# Plain decimals only: float() alone would also accept "1e2", "1_0", and "nan".
DECIMAL_RE = re.compile(r"^(\d+(\.\d*)?|\.\d+)$", re.ASCII)
MICROCHIP_NUMBER_RE = re.compile(r"^[A-Za-z0-9]{9,15}$")
BLANK_PET_VALUES = {
    "name": "",
    "species": "",
    "breed": "",
    "birth_date": "",
    "notes": "",
    "sex": "",
    "height_inches": "",
    "weight_lbs": "",
    "colors": "",
    "markings": "",
    "microchip_status": "unknown",
    "microchip_number": "",
}


def _delete_photo_file(photo_path):
    """Best-effort removal of a pet's stored photo from disk. Missing files
    are not an error — the DB row is the source of truth, not the file."""
    if not photo_path:
        return
    static_folder = current_app.static_folder
    full_path = os.path.join(static_folder, photo_path)
    try:
        os.remove(full_path)
    except OSError:
        pass


def _get_owned_pet_or_404(pet_id):
    """Every pet lookup is scoped to current_user.id, so one owner can never
    view, edit, or delete another owner's pet by guessing an id."""
    pet = Pet.query.filter_by(id=pet_id, owner_id=current_user.id).first()
    if pet is None:
        abort(404)
    return pet


def _parse_measure(raw, maximum, label, unit):
    """Returns (value, error) for an optional measurement field."""
    if not raw:
        return None, None
    message = f"{label} must be greater than 0 and at most {maximum} {unit}."
    if not DECIMAL_RE.match(raw):
        return None, message
    value = float(raw)
    if not 0 < value <= maximum:
        return None, message
    return value, None


def _validate_pet_form(form):
    errors = {}

    name = form.get("name", "").strip()
    species = form.get("species", "").strip()
    breed = form.get("breed", "").strip()
    birth_date_raw = form.get("birth_date", "").strip()
    notes = form.get("notes", "").strip()
    sex = form.get("sex", "").strip()
    colors = form.get("colors", "").strip()
    markings = form.get("markings", "").strip()
    microchip_status = form.get("microchip_status", "").strip() or "unknown"
    microchip_number = form.get("microchip_number", "").strip()

    if not name:
        errors["name"] = "Name is required."
    elif len(name) > MAX_NAME_LENGTH:
        errors["name"] = f"Name must be {MAX_NAME_LENGTH} characters or fewer."

    if not species:
        errors["species"] = "Species is required."

    birth_date = None
    if birth_date_raw:
        try:
            birth_date = datetime.strptime(birth_date_raw, "%Y-%m-%d").date()
            if birth_date > date.today():
                errors["birth_date"] = "Birth date cannot be in the future."
        except ValueError:
            errors["birth_date"] = "Use the format YYYY-MM-DD."

    if sex and sex not in SEX_VALUES:
        errors["sex"] = "Choose male, female, or unknown."

    height_inches, height_error = _parse_measure(
        form.get("height_inches", "").strip(), MAX_HEIGHT_INCHES, "Height", "inches"
    )
    if height_error:
        errors["height_inches"] = height_error

    weight_lbs, weight_error = _parse_measure(
        form.get("weight_lbs", "").strip(), MAX_WEIGHT_LBS, "Weight", "pounds"
    )
    if weight_error:
        errors["weight_lbs"] = weight_error

    if len(colors) > MAX_COLORS_LENGTH:
        errors["colors"] = f"Colors must be {MAX_COLORS_LENGTH} characters or fewer."
    if len(markings) > MAX_MARKINGS_LENGTH:
        errors["markings"] = (
            f"Markings must be {MAX_MARKINGS_LENGTH} characters or fewer."
        )

    if microchip_status not in MICROCHIP_VALUES:
        errors["microchip_status"] = "Choose a listed microchip status."
    if microchip_status == "chipped":
        if not microchip_number:
            errors["microchip_number"] = "Microchip number is required when chipped."
        elif not MICROCHIP_NUMBER_RE.match(microchip_number):
            errors["microchip_number"] = (
                "Microchip number must be 9-15 letters or digits."
            )
    else:
        microchip_number = ""

    cleaned = {
        "name": name,
        "species": species,
        "breed": breed or None,
        "birth_date": birth_date,
        "notes": notes or None,
        "sex": sex or None,
        "height_inches": height_inches,
        "weight_lbs": weight_lbs,
        "colors": colors or None,
        "markings": markings or None,
        "microchip_status": microchip_status,
        "microchip_number": microchip_number or None,
    }
    return errors, cleaned


def _save_photo(file_storage):
    """Validate and persist an uploaded pet photo (JPG/PNG, <= 5 MB).

    Returns the path to store in Pet.photo_path (relative to static/), or
    None if no file was submitted. Raises ValueError on an invalid file so
    the caller can surface it as an inline form error instead of a 500.
    """
    if file_storage is None or not file_storage.filename:
        return None

    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_ext = current_app.config["ALLOWED_PHOTO_EXTENSIONS"]
    allowed_mimetypes = current_app.config["ALLOWED_PHOTO_MIMETYPES"]

    if ext not in allowed_ext or file_storage.mimetype not in allowed_mimetypes:
        raise ValueError("Photo must be a JPG or PNG file.")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > current_app.config["MAX_CONTENT_LENGTH"]:
        raise ValueError("Photo must be 5 MB or smaller.")

    stored_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(os.path.join(upload_folder, stored_name))
    return f"uploads/{stored_name}"


@pets_bp.route("", methods=["GET"])
@login_required
def list_pets():
    pets = (
        Pet.query.filter_by(owner_id=current_user.id)
        .order_by(Pet.created_at.desc())
        .all()
    )
    return render_template("pets/list.html", pets=pets)


@pets_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_pet():
    errors = {}
    values = dict(BLANK_PET_VALUES)

    if request.method == "POST":
        errors, cleaned = _validate_pet_form(request.form)
        values.update(request.form)

        photo_path = None
        if not errors:
            try:
                photo_path = _save_photo(request.files.get("photo"))
            except ValueError as exc:
                errors["photo"] = str(exc)

        if not errors:
            pet = Pet(owner_id=current_user.id, **cleaned)
            if photo_path:
                pet.photo_path = photo_path
                pet.photo_uploaded_at = datetime.utcnow()
            db.session.add(pet)
            db.session.commit()
            flash(f"{pet.name} was added.", "success")
            return redirect(url_for("pets.view_pet", pet_id=pet.id))

    return render_template(
        "pets/form.html",
        errors=errors,
        values=values,
        species_choices=SPECIES_CHOICES,
        sex_choices=Pet.SEX_CHOICES,
        microchip_choices=Pet.MICROCHIP_CHOICES,
        pet=None,
        form_action=url_for("pets.new_pet"),
    )


@pets_bp.route("/<int:pet_id>", methods=["GET"])
@login_required
def view_pet(pet_id):
    pet = _get_owned_pet_or_404(pet_id)
    return render_template("pets/detail.html", pet=pet)


@pets_bp.route("/<int:pet_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pet(pet_id):
    pet = _get_owned_pet_or_404(pet_id)
    errors = {}
    values = {
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed or "",
        "birth_date": pet.birth_date.strftime("%Y-%m-%d") if pet.birth_date else "",
        "notes": pet.notes or "",
        "sex": pet.sex or "",
        "height_inches": format_measure(pet.height_inches),
        "weight_lbs": format_measure(pet.weight_lbs),
        "colors": pet.colors or "",
        "markings": pet.markings or "",
        "microchip_status": pet.microchip_status or "unknown",
        "microchip_number": pet.microchip_number or "",
    }

    if request.method == "POST":
        errors, cleaned = _validate_pet_form(request.form)
        values.update(request.form)

        photo_path = None
        if not errors:
            try:
                photo_path = _save_photo(request.files.get("photo"))
            except ValueError as exc:
                errors["photo"] = str(exc)

        if not errors:
            for field, value in cleaned.items():
                setattr(pet, field, value)
            if photo_path:
                old_photo_path = pet.photo_path
                pet.photo_path = photo_path
                pet.photo_uploaded_at = datetime.utcnow()
                _delete_photo_file(old_photo_path)
            db.session.commit()
            flash(f"{pet.name} was updated.", "success")
            return redirect(url_for("pets.view_pet", pet_id=pet.id))

    return render_template(
        "pets/form.html",
        errors=errors,
        values=values,
        species_choices=SPECIES_CHOICES,
        sex_choices=Pet.SEX_CHOICES,
        microchip_choices=Pet.MICROCHIP_CHOICES,
        pet=pet,
        form_action=url_for("pets.edit_pet", pet_id=pet.id),
    )


@pets_bp.route("/<int:pet_id>/delete", methods=["GET"])
@login_required
def confirm_delete_pet(pet_id):
    """Separate confirmation page (no JS) before the destructive POST."""
    pet = _get_owned_pet_or_404(pet_id)
    return render_template("pets/delete_confirm.html", pet=pet)


@pets_bp.route("/<int:pet_id>/delete", methods=["POST"])
@login_required
def delete_pet(pet_id):
    pet = _get_owned_pet_or_404(pet_id)
    name = pet.name
    photo_path = pet.photo_path
    db.session.delete(pet)
    db.session.commit()
    _delete_photo_file(photo_path)
    flash(f"{name} was deleted.", "success")
    return redirect(url_for("pets.list_pets"))
