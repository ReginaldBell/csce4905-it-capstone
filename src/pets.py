import os
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
from models import Pet

pets_bp = Blueprint("pets", __name__, url_prefix="/pets")

SPECIES_CHOICES = ["Dog", "Cat", "Bird", "Rabbit", "Other"]
MAX_NAME_LENGTH = 100


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


def _validate_pet_form(form):
    errors = {}

    name = form.get("name", "").strip()
    species = form.get("species", "").strip()
    breed = form.get("breed", "").strip()
    birth_date_raw = form.get("birth_date", "").strip()
    notes = form.get("notes", "").strip()

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

    cleaned = {
        "name": name,
        "species": species,
        "breed": breed or None,
        "birth_date": birth_date,
        "notes": notes or None,
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
    values = {"name": "", "species": "", "breed": "", "birth_date": "", "notes": ""}

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
            pet.name = cleaned["name"]
            pet.species = cleaned["species"]
            pet.breed = cleaned["breed"]
            pet.birth_date = cleaned["birth_date"]
            pet.notes = cleaned["notes"]
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
