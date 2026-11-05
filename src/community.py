"""Shared missing-pet reports, nearby browsing, and comments."""

from datetime import datetime
from math import asin, cos, isfinite, radians, sin, sqrt

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Report, ReportComment
from pets import SPECIES_CHOICES
from reports import _get_owned_report_or_404

community_bp = Blueprint("community", __name__, url_prefix="/community")
RADIUS_CHOICES = (5, 10, 25, 50)
PAGE_SIZE = 10


def _coordinates(form):
    try:
        latitude = float(form.get("latitude", ""))
        longitude = float(form.get("longitude", ""))
    except (TypeError, ValueError):
        raise ValueError("Choose a location on the map or use your current location.")
    if not (isfinite(latitude) and isfinite(longitude)):
        raise ValueError("Choose a valid location.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Choose a valid location.")
    return latitude, longitude


def _distance_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance, using the Haversine formula."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    distance = sin((lat2 - lat1) / 2) ** 2
    distance += cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * asin(sqrt(min(1, max(0, distance))))


def _shared_report_or_404(report_id):
    report = Report.query.filter_by(id=report_id, is_shared=True).first()
    if report is None or not report.pets:
        abort(404)
    return report


def _name_error(name):
    if not name or len(name) > 50:
        return "Enter a display name between 1 and 50 characters."
    return None


@community_bp.route("", methods=["GET"])
@login_required
def feed():
    errors = {}
    values = {"latitude": "", "longitude": "", "radius": "10", "species": "", "q": ""}
    values.update(request.args)
    posts = []
    has_more = False
    page = 1
    match_count = 0
    searched = bool(request.args)
    if searched:
        try:
            latitude, longitude = _coordinates(request.args)
        except ValueError as error:
            errors["location"] = str(error)
        try:
            radius = int(request.args.get("radius", "10"))
            page = int(request.args.get("page", "1"))
            if radius not in RADIUS_CHOICES or not 1 <= page <= 10000:
                raise ValueError
        except ValueError:
            errors["location"] = "Choose a listed distance and a valid page."
        species = request.args.get("species", "")
        search_text = request.args.get("q", "").strip().casefold()
        if species and species not in SPECIES_CHOICES:
            errors["filters"] = "Choose a listed pet type."
        if len(search_text) > 100:
            errors["filters"] = "Keep your search to 100 characters or fewer."
        if not errors:
            # The capstone dataset is small; a normal query and distance
            # calculation keep this readable without a spatial database.
            reports = (
                Report.query.filter(
                    Report.is_shared.is_(True),
                    Report.status == "open",
                    Report.latitude.isnot(None),
                    Report.longitude.isnot(None),
                    Report.report_pets.any(),
                )
                .order_by(Report.shared_at.desc(), Report.id.desc())
                .all()
            )
            matches = []
            for report in reports:
                if species and not any(pet.species == species for pet in report.pets):
                    continue
                public_text = " ".join(
                    [report.community_area or "", report.community_description or ""]
                    + [
                        f"{pet.name} {pet.species} {pet.breed or ''}"
                        for pet in report.pets
                    ]
                )
                if search_text and search_text not in public_text.casefold():
                    continue
                distance = _distance_miles(
                    latitude, longitude, report.latitude, report.longitude
                )
                if distance <= radius:
                    matches.append({"report": report, "distance": distance})
            matches.sort(key=lambda post: post["distance"])
            end = page * PAGE_SIZE
            match_count = len(matches)
            posts = matches[:end]
            has_more = len(matches) > end
    return render_template(
        "community/feed.html",
        posts=posts,
        values=values,
        errors=errors,
        searched=searched,
        has_more=has_more,
        page=page,
        radii=RADIUS_CHOICES,
        species_choices=SPECIES_CHOICES,
        match_count=match_count,
    )


@community_bp.route("/reports/<int:report_id>/share", methods=["GET", "POST"])
@login_required
def share_report(report_id):
    report = _get_owned_report_or_404(report_id)
    values = {
        "display_name": current_user.display_name or "",
        "community_area": report.community_area or "",
        "community_description": report.community_description or "",
        "latitude": report.latitude if report.latitude is not None else "",
        "longitude": report.longitude if report.longitude is not None else "",
    }
    errors = {}
    if request.method == "POST":
        values.update(request.form)
        name = request.form.get("display_name", "").strip()
        area = request.form.get("community_area", "").strip()
        description = request.form.get("community_description", "").strip()
        name_error = _name_error(name)
        if name_error:
            errors["display_name"] = name_error
        if not area or len(area) > 120:
            errors["community_area"] = (
                "Enter a general area between 1 and 120 characters."
            )
        if not description or len(description) > 1000:
            errors["community_description"] = (
                "Enter a description between 1 and 1,000 characters."
            )
        try:
            latitude, longitude = _coordinates(request.form)
        except ValueError as error:
            errors["location"] = str(error)
        if request.form.get("confirm_sharing") != "yes":
            errors["confirm_sharing"] = "Confirm that you want to share these details."
        if report.status != "open" or not report.pets:
            errors["form"] = "Only open reports with pets can be shared or updated."
        if not errors:
            current_user.display_name = name
            report.latitude, report.longitude = latitude, longitude
            report.community_area = area
            report.community_description = description
            report.is_shared = True
            if report.shared_at is None:
                report.shared_at = datetime.utcnow()
            db.session.commit()
            flash("Your report is shared with the community.", "success")
            return redirect(url_for("community.view_post", report_id=report.id))
    return render_template(
        "community/share.html", report=report, values=values, errors=errors
    )


@community_bp.route("/reports/<int:report_id>/unshare", methods=["POST"])
@login_required
def unshare_report(report_id):
    report = _get_owned_report_or_404(report_id)
    report.is_shared = False
    db.session.commit()
    flash("Your report was removed from the community.", "success")
    return redirect(url_for("reports.view_report", report_id=report.id))


@community_bp.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def view_post(report_id):
    report = _shared_report_or_404(report_id)
    return render_template(
        "community/detail.html", report=report, errors={}, comment_values={}
    )


@community_bp.route("/reports/<int:report_id>/comments", methods=["POST"])
@login_required
def add_comment(report_id):
    report = _shared_report_or_404(report_id)
    if report.status != "open":
        flash("This report is resolved. New comments are closed.", "info")
        return redirect(url_for("community.view_post", report_id=report.id))
    name = request.form.get("display_name", "").strip()
    body = request.form.get("body", "").strip()
    errors = {}
    name_error = _name_error(name)
    if name_error:
        errors["display_name"] = name_error
    if not body or len(body) > 1000:
        errors["body"] = "Enter a comment between 1 and 1,000 characters."
    if errors:
        return render_template(
            "community/detail.html",
            report=report,
            errors=errors,
            comment_values={"display_name": name, "body": body},
        )
    current_user.display_name = name
    db.session.add(
        ReportComment(report_id=report.id, author_id=current_user.id, body=body)
    )
    db.session.commit()
    return redirect(
        url_for("community.view_post", report_id=report.id, _anchor="comments")
    )


@community_bp.route(
    "/reports/<int:report_id>/comments/<int:comment_id>/delete", methods=["POST"]
)
@login_required
def delete_comment(report_id, comment_id):
    _shared_report_or_404(report_id)
    comment = ReportComment.query.filter_by(
        id=comment_id,
        report_id=report_id,
        author_id=current_user.id,
    ).first()
    if comment is None:
        abort(404)
    db.session.delete(comment)
    db.session.commit()
    return redirect(
        url_for("community.view_post", report_id=report_id, _anchor="comments")
    )
