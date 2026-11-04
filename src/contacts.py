import re

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
from models import Contact

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

CATEGORY_CHOICES = [
    "Veterinarian",
    "Animal Shelter",
    "Animal Control",
    "Microchip Registry",
    "Groomer",
    "Other",
]
MAX_NAME_LENGTH = 100

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9()+\-.\s]{7,30}$")


def _get_owned_contact_or_404(contact_id):
    """Every contact lookup is scoped to current_user.id, same as pets."""
    contact = Contact.query.filter_by(id=contact_id, owner_id=current_user.id).first()
    if contact is None:
        abort(404)
    return contact


def _validate_contact_form(form):
    errors = {}

    category = form.get("category", "").strip()
    name = form.get("name", "").strip()
    phone = form.get("phone", "").strip()
    email = form.get("email", "").strip()
    notes = form.get("notes", "").strip()

    if not category:
        errors["category"] = "Category is required."
    elif len(category) > 50:
        errors["category"] = "Category must be 50 characters or fewer."

    if not name:
        errors["name"] = "Name is required."
    elif len(name) > MAX_NAME_LENGTH:
        errors["name"] = f"Name must be {MAX_NAME_LENGTH} characters or fewer."

    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Enter a valid phone number."

    if email and not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."

    if not phone and not email:
        errors["form"] = "Enter a phone number or an email address."

    cleaned = {
        "category": category,
        "name": name,
        "phone": phone or None,
        "email": email or None,
        "notes": notes or None,
    }
    return errors, cleaned


@contacts_bp.route("", methods=["GET"])
@login_required
def list_contacts():
    contacts = (
        Contact.query.filter_by(owner_id=current_user.id)
        .order_by(Contact.category.asc(), Contact.name.asc())
        .all()
    )

    grouped = {}
    for contact in contacts:
        grouped.setdefault(contact.category, []).append(contact)

    return render_template(
        "contacts/list.html", grouped_contacts=sorted(grouped.items())
    )


@contacts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_contact():
    errors = {}
    values = {"category": "", "name": "", "phone": "", "email": "", "notes": ""}

    if request.method == "POST":
        errors, cleaned = _validate_contact_form(request.form)
        values.update(request.form)

        if not errors:
            contact = Contact(owner_id=current_user.id, **cleaned)
            db.session.add(contact)
            db.session.commit()
            flash(f"{contact.name} was added.", "success")
            return redirect(url_for("contacts.view_contact", contact_id=contact.id))

    return render_template(
        "contacts/form.html",
        errors=errors,
        values=values,
        category_choices=CATEGORY_CHOICES,
        contact=None,
        form_action=url_for("contacts.new_contact"),
    )


@contacts_bp.route("/<int:contact_id>", methods=["GET"])
@login_required
def view_contact(contact_id):
    contact = _get_owned_contact_or_404(contact_id)
    return render_template("contacts/detail.html", contact=contact)


@contacts_bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id):
    contact = _get_owned_contact_or_404(contact_id)
    errors = {}
    values = {
        "category": contact.category,
        "name": contact.name,
        "phone": contact.phone or "",
        "email": contact.email or "",
        "notes": contact.notes or "",
    }

    if request.method == "POST":
        errors, cleaned = _validate_contact_form(request.form)
        values.update(request.form)

        if not errors:
            contact.category = cleaned["category"]
            contact.name = cleaned["name"]
            contact.phone = cleaned["phone"]
            contact.email = cleaned["email"]
            contact.notes = cleaned["notes"]
            db.session.commit()
            flash(f"{contact.name} was updated.", "success")
            return redirect(url_for("contacts.view_contact", contact_id=contact.id))

    return render_template(
        "contacts/form.html",
        errors=errors,
        values=values,
        category_choices=CATEGORY_CHOICES,
        contact=contact,
        form_action=url_for("contacts.edit_contact", contact_id=contact.id),
    )


@contacts_bp.route("/<int:contact_id>/delete", methods=["GET"])
@login_required
def confirm_delete_contact(contact_id):
    contact = _get_owned_contact_or_404(contact_id)
    return render_template("contacts/delete_confirm.html", contact=contact)


@contacts_bp.route("/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete_contact(contact_id):
    contact = _get_owned_contact_or_404(contact_id)
    name = contact.name
    db.session.delete(contact)
    db.session.commit()
    flash(f"{name} was deleted.", "success")
    return redirect(url_for("contacts.list_contacts"))
