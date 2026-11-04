"""Generated outputs for a missing-pet report: agency email (card 6),
phone script (card 7), social post (card 8), and flyer (card 9). Nothing
here is persisted — every route builds its text on the fly from the
current state of the Report, its Pets, and (where relevant) a Contact.

Email and phone script both need the user to pick which contact the
output is for; social post and flyer don't (they're not addressed to
anyone), so only those two share the pick_contact.html picker.
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


def _owned_contacts():
    return (
        Contact.query.filter_by(owner_id=current_user.id)
        .order_by(Contact.category.asc(), Contact.name.asc())
        .all()
    )


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


def build_phone_script(report, contact):
    """Returns a single script to read when calling a contact about this
    report."""
    is_plural = len(report.pets) != 1
    noun = "pets" if is_plural else "pet"
    article = "" if is_plural else "a "

    last_seen_at = (
        report.last_seen_at.strftime("%Y-%m-%d %H:%M UTC")
        if report.last_seen_at
        else "an unknown time"
    )

    lines = [
        f"Hi, I'm calling {contact.name} to report {article}missing {noun}.",
        "",
        f"Pet(s): {_pet_list_text(report)}",
        f"Last seen location: {report.last_seen_location}",
        f"Last seen time: {last_seen_at}",
    ]
    if report.notes:
        lines.append(f"Additional details: {report.notes}")
    lines += [
        "",
        "Could you let me know if you have anything on file matching this "
        "description, or what steps I should take next?",
        "",
        f"You can reach me at {current_user.email} if you need to follow up.",
        "",
        "Thank you for your time.",
    ]
    return "\n".join(lines)


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

    return render_template(
        "outputs/pick_contact.html",
        report=report,
        contacts=_owned_contacts(),
        heading="Email an agency",
        target_endpoint="outputs.email_preview",
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


@outputs_bp.route("/<int:report_id>/phone-script", methods=["GET"])
@login_required
def pick_phone_contact(report_id):
    report = _get_owned_report_or_404(report_id)
    redirect_response = _require_report_pets_or_redirect(report)
    if redirect_response:
        return redirect_response

    return render_template(
        "outputs/pick_contact.html",
        report=report,
        contacts=_owned_contacts(),
        heading="Generate a phone script",
        target_endpoint="outputs.phone_script_preview",
    )


@outputs_bp.route("/<int:report_id>/phone-script/<int:contact_id>", methods=["GET"])
@login_required
def phone_script_preview(report_id, contact_id):
    report = _get_owned_report_or_404(report_id)
    redirect_response = _require_report_pets_or_redirect(report)
    if redirect_response:
        return redirect_response

    contact = _get_owned_contact_or_404(contact_id)
    script = build_phone_script(report, contact)

    return render_template(
        "outputs/phone_script_preview.html",
        report=report,
        contact=contact,
        script=script,
    )
