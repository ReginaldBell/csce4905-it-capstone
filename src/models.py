from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    pets = db.relationship(
        "Pet", backref="owner", cascade="all, delete-orphan", lazy=True
    )
    contacts = db.relationship(
        "Contact", backref="owner", cascade="all, delete-orphan", lazy=True
    )
    reports = db.relationship(
        "Report", backref="owner", cascade="all, delete-orphan", lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Pet(db.Model):
    __tablename__ = "pets"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)
    breed = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    photo_path = db.Column(db.String(255))
    photo_uploaded_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Deleting a pet drops its links into any missing-pet reports, but not
    # the reports themselves (a report can cover more than one pet).
    report_pets = db.relationship(
        "ReportPet", backref="pet", cascade="all, delete-orphan", lazy=True
    )

    # TODO (out of scope for Sprint 1, picked up in Sprint 2): contacts
    # live on their own Contact model. Generated outputs (email/phone
    # script/social post/flyer text) read from Report + Pet + Contact but
    # are not stored themselves.


class Report(db.Model):
    """A missing-pet report. Covers one or more pets via ReportPet."""

    __tablename__ = "reports"

    STATUSES = ("open", "found", "closed")

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    status = db.Column(db.String(20), nullable=False, default="open")
    last_seen_at = db.Column(db.DateTime)
    last_seen_location = db.Column(db.String(255))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    closed_at = db.Column(db.DateTime)

    report_pets = db.relationship(
        "ReportPet", backref="report", cascade="all, delete-orphan", lazy=True
    )
    status_events = db.relationship(
        "ReportStatusEvent",
        backref="report",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="ReportStatusEvent.changed_at",
    )

    @property
    def pets(self):
        """The Pet rows this report covers, in the order they were added."""
        return [rp.pet for rp in self.report_pets]


class ReportPet(db.Model):
    """Join row: one pet covered by one missing-pet report."""

    __tablename__ = "report_pets"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True
    )
    pet_id = db.Column(db.Integer, db.ForeignKey("pets.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ReportStatusEvent(db.Model):
    """One row per status change on a report, oldest first. The initial
    creation is logged too, with from_status=None."""

    __tablename__ = "report_status_events"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True
    )
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Contact(db.Model):
    """An external contact (vet, shelter, animal control, ...), grouped by
    category in the UI. Scoped per owner, same as Pet."""

    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    category = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
