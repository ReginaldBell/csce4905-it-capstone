"""Generated outputs for a missing-pet report: agency email (card 6),
phone script (card 7), social post (card 8), and flyer (card 9). Nothing
here is persisted — every route builds its text on the fly from the
current state of the Report, its Pets, and (where relevant) a Contact.
"""

from urllib.parse import quote

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from models import Contact

from reports import _get_owned_report_or_404

outputs_bp = Blueprint("outputs", __name__, url_prefix="/reports")


def _get_owned_contact_or_404(contact_id):
    contact = Contact.query.filter_by(id=contact_id, owner_id=current_user.id).first()
    if contact is None:
        abort(404)
    return contact


def _pet_list_text(report):
    pets = report.pets
    if not pets:
        # Defense in depth: every route that reaches this already checks
        # report.pets and redirects before calling it, but don't crash on
        # descriptions[-1] if a future caller forgets to.
        return "no pets on file"
    descriptions = [
        f"{pet.name} ({pet.species}{', ' + pet.breed if pet.breed else ''})"
        for pet in pets
    ]
    if len(descriptions) == 1:
        return descriptions[0]
    if len(descriptions) == 2:
        return f"{descriptions[0]} and {descriptions[1]}"
    return ", ".join(descriptions[:-1]) + f", and {descriptions[-1]}"


def build_agency_email(report):
    """Returns (subject, body) for an email to an agency about this report."""
    pet_names = ", ".join(pet.name for pet in report.pets)
    is_plural = len(report.pets) != 1
    noun = "pets" if is_plural else "pet"
    article = "" if is_plural else "a "

    subject = f"Missing Pet Report: {pet_names}"

    last_seen_at = (
        report.last_seen_at.strftime("%Y-%m-%d %H:%M")
        if report.last_seen_at
        else "an unknown time"
    )

    lines = [
        "Hello,",
        "",
        f"I am writing to report {article}missing {noun}: {_pet_list_text(report)}.",
        "",
        f"Last seen location: {report.last_seen_location}",
        f"Last seen time: {last_seen_at}",
    ]
    if report.notes:
        lines.append(f"Additional details: {report.notes}")
    lines += [
        "",
        f"Please contact me at {current_user.email} with any information.",
        "",
        "Thank you for your help.",
    ]
    return subject, "\n".join(lines)


def _require_report_pets_or_redirect(report):
    """Pets can be deleted independently of the report that references
    them (deleting a pet drops its report_pets link, not the report
    itself), so a report can legitimately end up with zero pets by the
    time someone generates an output for it. Returns a redirect response
    if that's the case, None otherwise."""
    if not report.pets:
        flash(
            "This report has no pets attached — nothing to generate an output about.",
            "error",
        )
        return redirect(url_for("reports.view_report", report_id=report.id))
    return None


@outputs_bp.route("/<int:report_id>/email", methods=["GET"])
@login_required
def pick_email_contact(report_id):
    report = _get_owned_report_or_404(report_id)
    redirect_response = _require_report_pets_or_redirect(report)
    if redirect_response:
        return redirect_response

    contacts = (
        Contact.query.filter_by(owner_id=current_user.id)
        .order_by(Contact.category.asc(), Contact.name.asc())
        .all()
    )
    return render_template(
        "outputs/pick_email_contact.html", report=report, contacts=contacts
    )


@outputs_bp.route("/<int:report_id>/email/<int:contact_id>", methods=["GET"])
@login_required
def email_preview(report_id, contact_id):
    report = _get_owned_report_or_404(report_id)
    redirect_response = _require_report_pets_or_redirect(report)
    if redirect_response:
        return redirect_response

    contact = _get_owned_contact_or_404(contact_id)

    subject, body = build_agency_email(report)
    mailto_url = None
    if contact.email:
        mailto_url = (
            f"mailto:{quote(contact.email)}?subject={quote(subject)}&body={quote(body)}"
        )

    return render_template(
        "outputs/email_preview.html",
        report=report,
        contact=contact,
        subject=subject,
        body=body,
        mailto_url=mailto_url,
    )


# Report.notes is an unbounded Text column (same as Pet.notes and
# Contact.notes elsewhere in the app) with no length cap on the form —
# fine everywhere else, but the flyer has a hard "one page" requirement
# that free text of unbounded length can blow past: page-break-inside:
# avoid only stops an *avoidable* break, it can't keep a box on one page
# once that box is taller than the page itself. Bounded, deterministic
# truncation is the only thing that actually guarantees one page here,
# short of adding a layout/PDF engine this project has no other need for.
MAX_FLYER_NOTES_LENGTH = 200


def _truncate_for_flyer(text, max_length=MAX_FLYER_NOTES_LENGTH):
    if text is None or len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


@outputs_bp.route("/<int:report_id>/flyer", methods=["GET"])
@login_required
def flyer_preview(report_id):
    report = _get_owned_report_or_404(report_id)
    redirect_response = _require_report_pets_or_redirect(report)
    if redirect_response:
        return redirect_response

    cover_pet = next((pet for pet in report.pets if pet.photo_path), None)
    pet_names = ", ".join(pet.name for pet in report.pets)
    species_text = ", ".join(sorted({pet.species for pet in report.pets}))
    flyer_notes = _truncate_for_flyer(report.notes) if report.notes else None

    return render_template(
        "outputs/flyer_preview.html",
        report=report,
        cover_pet=cover_pet,
        pet_names=pet_names,
        species_text=species_text,
        flyer_notes=flyer_notes,
    )
