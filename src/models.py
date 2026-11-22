from datetime import date, datetime
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import false
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(50))
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    # Part of the login session id; raising it ends older sessions.
    session_version = db.Column(
        db.Integer, nullable=False, default=1, server_default="1"
    )
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
    comments = db.relationship(
        "ReportComment", backref="author", cascade="all, delete-orphan", lazy=True
    )
    password_reset_tokens = db.relationship(
        "PasswordResetToken", backref="user", cascade="all, delete-orphan", lazy=True
    )

    def get_id(self):
        return f"{self.id}:{self.session_version or 1}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PasswordResetToken(db.Model):
    """A single-use reset link. Only the SHA-256 of the token is stored."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def _plural(count, unit):
    return f"{count} {unit}" if count == 1 else f"{count} {unit}s"


def format_measure(value):
    """Show 12.0 as "12" without rounding a value the owner entered."""
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    text = str(value)
    # The pet form rejects exponents, so 1e-05 must be written as 0.00001.
    return format(Decimal(text), "f") if "e" in text else text


class Pet(db.Model):
    __tablename__ = "pets"

    SEX_CHOICES = (("male", "Male"), ("female", "Female"), ("unknown", "Unknown"))
    MICROCHIP_CHOICES = (
        ("unknown", "Unknown"),
        ("chipped", "Chipped"),
        ("not_chipped", "Not chipped"),
    )

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)
    breed = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    sex = db.Column(db.String(20))
    height_inches = db.Column(db.Float)
    weight_lbs = db.Column(db.Float)
    colors = db.Column(db.String(100))
    markings = db.Column(db.String(255))
    microchip_status = db.Column(
        db.String(20), default="unknown", server_default="unknown"
    )
    microchip_number = db.Column(db.String(15))

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

    @property
    def age_display(self):
        """Age from birth_date in whole completed months, as of today."""
        if self.birth_date is None:
            return None
        today = date.today()
        months = (today.year - self.birth_date.year) * 12
        months += today.month - self.birth_date.month
        if today.day < self.birth_date.day:
            months -= 1
        if months < 1:
            return "Under 1 month"
        years, remainder = divmod(months, 12)
        if years == 0:
            return _plural(remainder, "month")
        if remainder == 0:
            return _plural(years, "year")
        return f"{_plural(years, 'year')}, {_plural(remainder, 'month')}"

    @property
    def sex_label(self):
        return dict(self.SEX_CHOICES).get(self.sex)

    @property
    def microchip_label(self):
        return dict(self.MICROCHIP_CHOICES).get(self.microchip_status or "unknown")

    @property
    def height_display(self):
        return format_measure(self.height_inches)

    @property
    def weight_display(self):
        return format_measure(self.weight_lbs)


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

    # Sharing is separate from the owner's private report details.
    is_shared = db.Column(
        db.Boolean, nullable=False, default=False, server_default=false()
    )
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    community_area = db.Column(db.String(120))
    community_description = db.Column(db.Text)
    shared_at = db.Column(db.DateTime)

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
    comments = db.relationship(
        "ReportComment",
        backref="report",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="ReportComment.created_at, ReportComment.id",
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


class ReportComment(db.Model):
    __tablename__ = "report_comments"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True
    )
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    body = db.Column(db.String(1000), nullable=False)
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
    address = db.Column(db.String(255))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
