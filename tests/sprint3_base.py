"""Shared setup for Sprint 3 feature tests. Not collected as a test module.

Tests are written against SPRINT3_CONTRACT.md. New columns and models are read with
getattr or model_or_fail so an unbuilt feature reports a clear FAIL, not an import error
that would hide every other test in the file.
"""

import importlib
import os
import re
import tempfile
import unittest
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "sprint3-tests-only")

import models
from app import create_app
from config import Config
from extensions import db
from models import Contact, Pet, User

import sprint3_data

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"sprint3 synthetic image"
MISSING = object()
PET_FORM_FIELDS = (
    "name", "species", "breed", "birth_date", "notes", "sex", "height_inches",
    "weight_lbs", "colors", "markings", "microchip_status", "microchip_number",
)
CONTACT_FORM_FIELDS = ("category", "name", "phone", "email", "address", "notes")


class Sprint3Config(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = True
    MAIL_BACKEND = "memory"
    PASSWORD_RESET_TTL_MINUTES = 60
    LOGIN_LIMIT = 5
    LOGIN_WINDOW_SECONDS = 900
    RESET_LIMIT = 3
    RESET_WINDOW_SECONDS = 3600


class PageParser(HTMLParser):
    """Collect form controls, labels, and element text by id."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
            "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.controls = []
        self.label_for = set()
        self.text_by_id = {}
        self._open_ids = []
        self._label_depth = 0
        self._current = None
        self._select = None
        self._fieldsets = []
        self.hidden_ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or "" for key, value in attrs}
        if attrs.get("id") and ("hidden" in attrs or attrs.get("aria-hidden") == "true"
                                or "display:none" in attrs.get("style", "").replace(" ", "")):
            self.hidden_ids.add(attrs["id"])
        if tag == "fieldset":
            self._fieldsets.append(attrs)
        if tag == "label":
            self._label_depth += 1
            if attrs.get("for"):
                self.label_for.add(attrs["for"])
        if tag in ("input", "select", "textarea") and attrs.get("name"):
            control = {"tag": tag, "attrs": attrs, "wrapped": self._label_depth > 0,
                       "value": attrs.get("value", "") if tag == "input" else "",
                       "fieldset": self._fieldsets[-1] if self._fieldsets else {}}
            self.controls.append(control)
            if tag == "textarea":
                self._current = control
            if tag == "select":
                self._select = control
        if tag == "option" and self._select is not None and "selected" in attrs:
            self._select["value"] = attrs.get("value", "")
        if tag not in self.VOID:
            self._open_ids.append((tag, attrs.get("id")))
            if attrs.get("id"):
                self.text_by_id.setdefault(attrs["id"], "")
        elif attrs.get("id"):
            self.text_by_id.setdefault(attrs["id"], "")

    def handle_endtag(self, tag):
        if tag == "fieldset" and self._fieldsets:
            self._fieldsets.pop()
        if tag == "label" and self._label_depth:
            self._label_depth -= 1
        if tag == "textarea":
            self._current = None
        if tag == "select":
            self._select = None
        for index in range(len(self._open_ids) - 1, -1, -1):
            if self._open_ids[index][0] == tag:
                del self._open_ids[index:]
                break

    def handle_data(self, data):
        if self._current is not None:
            self._current["value"] += data
        for _tag, element_id in self._open_ids:
            if element_id:
                self.text_by_id[element_id] += data

    def named(self, name):
        return [c for c in self.controls if c["attrs"].get("name") == name]

    def unlabeled(self):
        missing = []
        for control in self.controls:
            attrs = control["attrs"]
            if attrs.get("type") in ("hidden", "submit", "button", "reset", "image"):
                continue
            if control["wrapped"] or attrs.get("id") in self.label_for:
                continue
            if attrs.get("aria-label") or attrs.get("aria-labelledby"):
                continue
            missing.append(attrs["name"])
        return missing


def parse_page(response_or_text):
    text = response_or_text
    if hasattr(response_or_text, "get_data"):
        text = response_or_text.get_data(as_text=True)
    parser = PageParser()
    parser.feed(text)
    return parser


def form_text(value):
    return "" if value is None else str(value)


class Sprint3TestCase(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.fixtures = sprint3_data.load_all()
        cls.users = sprint3_data.by_key(cls.fixtures["users"]["users"])
        cls.pets = sprint3_data.by_key(cls.fixtures["pets"]["pets"])
        cls.contacts = sprint3_data.by_key(cls.fixtures["contacts"]["contacts"])
        cls.invalid = cls.fixtures["invalid_inputs"]
        cls.reset_cases = cls.fixtures["password_reset_cases"]

    def setUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.app = create_app(Sprint3Config)
        self.app.static_folder = self.files.name
        self.upload_dir = Path(self.files.name) / "uploads"
        self.upload_dir.mkdir()
        self.app.config["UPLOAD_FOLDER"] = str(self.upload_dir)
        self.user_ids = {}
        with self.app.app_context():
            db.create_all()
            for key in ("owner", "other"):
                row = self.users[key]
                user = User(email=row["email"], display_name=row["display_name"])
                user.set_password(row["password"])
                db.session.add(user)
                db.session.flush()
                self.user_ids[key] = user.id
            db.session.commit()
        self.owner = self.app.test_client()
        self.other = self.app.test_client()
        self.guest = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.files.cleanup()

    # Requests ---------------------------------------------------------------

    def csrf(self, client, addr=None):
        kwargs = self._addr(addr)
        page = client.get("/login", **kwargs)
        if page.status_code == 302:
            page = client.get("/pets", **kwargs)
        match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data)
        self.assertIsNotNone(match, "no CSRF token found")
        return match.group(1).decode()

    @staticmethod
    def _addr(addr):
        return {"environ_overrides": {"REMOTE_ADDR": addr}} if addr else {}

    def post(self, client, route, values=None, follow=False, addr=None, headers=None):
        data = dict(values or {})
        data["csrf_token"] = self.csrf(client, addr)
        kwargs = self._addr(addr)
        if headers:
            kwargs["headers"] = headers
        if any(isinstance(value, tuple) for value in data.values()):
            kwargs["content_type"] = "multipart/form-data"
        return client.post(route, data=data, follow_redirects=follow, **kwargs)

    def login(self, client, key="owner", password=None, addr=None, next_url=None):
        row = self.users[key]
        route = "/login"
        query = {"query_string": {"next": next_url}} if next_url is not None else {}
        data = {"email": row["email"], "password": password or row["password"],
                "csrf_token": self.csrf(client, addr)}
        return client.post(route, data=data, **query, **self._addr(addr))

    def login_both(self):
        self.assertEqual(self.login(self.owner, "owner").status_code, 302)
        self.assertEqual(self.login(self.other, "other").status_code, 302)

    def logout(self, client):
        return self.post(client, "/logout")

    def assert_redirects_to_login(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    # Data -------------------------------------------------------------------

    def pet_values(self, key, **changes):
        row = self.pets[key]
        values = {field: form_text(row[field]) for field in PET_FORM_FIELDS}
        values.update(changes)
        return values

    def contact_values(self, key, **changes):
        row = self.contacts[key]
        values = {field: form_text(row[field]) for field in CONTACT_FORM_FIELDS}
        values.update(changes)
        return values

    def seed_pet(self, owner="owner", name="Seed Pet", species="Dog", **fields):
        with self.app.app_context():
            pet = Pet(owner_id=self.user_ids[owner], name=name, species=species, **fields)
            db.session.add(pet)
            db.session.commit()
            return pet.id

    def seed_contact(self, key):
        row = self.contacts[key]
        with self.app.app_context():
            contact = Contact(owner_id=self.user_ids[row["owner"]], category=row["category"],
                              name=row["name"], phone=row["phone"], email=row["email"])
            db.session.add(contact)
            db.session.commit()
            return contact.id

    def pet_count(self):
        with self.app.app_context():
            return Pet.query.count()

    def contact_count(self):
        with self.app.app_context():
            return Contact.query.count()

    def pet_snapshot(self, pet_id):
        with self.app.app_context():
            pet = db.session.get(Pet, pet_id)
            return None if pet is None else {
                "owner_id": pet.owner_id, "name": pet.name, "species": pet.species,
                "breed": pet.breed, "notes": pet.notes, "photo_path": pet.photo_path,
                "updated_at": pet.updated_at,
            }

    def user_value(self, key, field):
        with self.app.app_context():
            return getattr(db.session.get(User, self.user_ids[key]), field, MISSING)

    def model_or_fail(self, name):
        model = getattr(models, name, None)
        if model is None:
            self.fail(f"models.{name} is required by the Sprint 3 contract")
        return model

    def auth_attempt_model(self):
        """The contract places AuthAttempt in src/rate_limit.py, not models.py."""
        try:
            rate_limit = importlib.import_module("rate_limit")
        except ModuleNotFoundError:
            self.fail("src/rate_limit.py is required by the Sprint 3 contract")
        model = getattr(rate_limit, "AuthAttempt", None)
        if model is None:
            self.fail("rate_limit.AuthAttempt is required by the Sprint 3 contract")
        return model

    def outbox(self):
        return list(self.app.extensions.get("mail_outbox", []))

    # Assertions -------------------------------------------------------------

    def assert_field_error(self, response, field):
        """The control is tied to non-empty error text through aria-describedby."""
        page = parse_page(response)
        controls = page.named(field)
        self.assertTrue(controls, f"no control named {field}")
        for control in controls:
            for element_id in control["attrs"].get("aria-describedby", "").split():
                if page.text_by_id.get(element_id, "").strip():
                    return
        self.fail(f"{field} has no error linked with aria-describedby")

    def assert_group_error(self, response, field, message):
        """Each control in a group, or its fieldset, points to the visible error."""
        page = parse_page(response)
        controls = page.named(field)
        self.assertTrue(controls, f"no control named {field}")
        for control in controls:
            ids = (control["attrs"].get("aria-describedby", "").split()
                   + control["fieldset"].get("aria-describedby", "").split())
            visible = [element_id for element_id in ids
                       if element_id not in page.hidden_ids
                       and message in page.text_by_id.get(element_id, "")]
            self.assertTrue(visible, f"{field} is not linked to visible error: {message}")

    def control_value(self, response, field):
        controls = parse_page(response).named(field)
        self.assertTrue(controls, f"no control named {field}")
        return unescape(controls[0]["value"]).strip()

    def page_text(self, response):
        return unescape(response.get_data(as_text=True))
