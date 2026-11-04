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

    # TODO (out of scope for Sprint 1, picked up in Sprint 2): the Report
    # Missing workflow and generated outputs (email/phone script/social
    # post/flyer text) will reference Pet in a later card. Do not build
    # against those here.


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
