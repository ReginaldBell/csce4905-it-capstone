"""Load the fictional community examples into a development database."""

import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import click
from flask import current_app
from flask.cli import with_appcontext

from extensions import db
from models import Pet, Report, ReportComment, ReportPet, ReportStatusEvent, User

SAMPLE_FOLDER = Path(__file__).parent / "sample_data"
DEMO_PASSWORD = "DemoPass123!"


def load_demo_data():
    data = json.loads(
        (SAMPLE_FOLDER / "community_demo.json").read_text(encoding="utf-8")
    )
    emails = [row["email"] for row in data["users"]]
    existing = User.query.filter(User.email.in_(emails)).count()
    if existing == len(emails):
        return False
    if existing:
        raise click.ClickException(
            "Some demo emails already exist. No records were changed. "
            "Use a separate development database for the full sample set."
        )

    users, pets = {}, {}
    copied_photos = []
    now = datetime.utcnow()
    try:
        for row in data["users"]:
            user = User(email=row["email"], display_name=row["display_name"])
            user.set_password(DEMO_PASSWORD)
            db.session.add(user)
            db.session.flush()
            users[user.email] = user
            for sample in row["pets"]:
                pet = Pet(
                    owner_id=user.id,
                    name=sample["name"],
                    species=sample["species"],
                    breed=sample["breed"],
                    birth_date=(
                        date.fromisoformat(sample["birth_date"])
                        if sample["birth_date"]
                        else None
                    ),
                    notes=sample["notes"],
                )
                if sample.get("photo"):
                    filename = f"demo-{uuid4().hex}.png"
                    destination = Path(current_app.config["UPLOAD_FOLDER"]) / filename
                    shutil.copyfile(
                        SAMPLE_FOLDER / "photos" / sample["photo"], destination
                    )
                    copied_photos.append(destination)
                    pet.photo_path = f"uploads/{filename}"
                    pet.photo_uploaded_at = now
                db.session.add(pet)
                pets[(user.email, pet.name)] = pet
        db.session.flush()
        for row in data["reports"]:
            created_at = now - timedelta(hours=row["hours_ago"])
            report = Report(
                owner_id=users[row["owner_email"]].id,
                status=row["status"],
                last_seen_at=created_at if row["last_seen_known"] else None,
                last_seen_location=row["private_location"],
                notes=row["private_notes"],
                created_at=created_at,
                is_shared=row["is_shared"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                community_area=row["community_area"],
                community_description=row["community_description"],
                shared_at=created_at if row["is_shared"] else None,
                closed_at=now if row["status"] != "open" else None,
            )
            db.session.add(report)
            db.session.flush()
            for name in row["pets"]:
                db.session.add(
                    ReportPet(
                        report_id=report.id, pet_id=pets[(row["owner_email"], name)].id
                    )
                )
            db.session.add(
                ReportStatusEvent(
                    report_id=report.id, to_status="open", changed_at=created_at
                )
            )
            if row["status"] != "open":
                db.session.add(
                    ReportStatusEvent(
                        report_id=report.id,
                        from_status="open",
                        to_status=row["status"],
                        changed_at=now,
                    )
                )
            for index, comment in enumerate(row["comments"]):
                db.session.add(
                    ReportComment(
                        report_id=report.id,
                        author_id=users[comment["author_email"]].id,
                        body=comment["body"],
                        created_at=created_at + timedelta(minutes=index + 1),
                    )
                )
        db.session.commit()
    except Exception:
        db.session.rollback()
        for path in copied_photos:
            path.unlink(missing_ok=True)
        raise
    return True


@click.command("seed-community-demo")
@with_appcontext
def seed_community_demo_command():
    """Add fictional users/pets/reports to a development DB, with known demo logins.

    Run upgrade-community first. Re-running keeps existing demo changes and adds
    no duplicates. This command never runs automatically when the app starts.
    """
    if load_demo_data():
        click.echo("Added 12 fictional users, 25 pets, 24 reports, and 8 comments.")
    else:
        click.echo("Demo users already exist; their records and passwords were kept.")
    click.echo(
        f"Development logins: demo01@example.com through demo12@example.com / {DEMO_PASSWORD}"
    )
    click.echo("Test search center: latitude=33.21, longitude=-97.13 (Denton, Texas).")
