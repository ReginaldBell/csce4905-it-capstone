"""Run: python -m unittest discover -s tests -v (with src on PYTHONPATH)."""

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "settings-tests-only")

from app import create_app
from config import Config
from extensions import db
from models import Pet, User


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = True


class SettingsUiTests(unittest.TestCase):
    def setUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.app = create_app(TestConfig)
        self.app.config["UPLOAD_FOLDER"] = str(Path(self.files.name) / "uploads")
        with self.app.app_context():
            db.create_all()
            owner = User(email="owner@example.com", display_name="Original")
            other = User(email="other@example.com")
            for user in (owner, other):
                user.set_password("DemoPass123!")
            db.session.add_all([owner, other])
            db.session.flush()
            first = Pet(owner_id=owner.id, name="Biscuit", species="Dog")
            second = Pet(owner_id=owner.id, name="Luna", species="Cat")
            foreign = Pet(owner_id=other.id, name="Hidden", species="Dog")
            db.session.add_all([first, second, foreign])
            db.session.commit()
            self.owner_id = owner.id
            self.pet_id, self.second_id = first.id, second.id
            self.foreign_id = foreign.id
        self.client = self.app.test_client()
        self.post("/login", {"email": "owner@example.com", "password": "DemoPass123!"}, "/login")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.files.cleanup()

    def post(self, route, values, token_route="/settings"):
        page = self.client.get(token_route)
        token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1)
        return self.client.post(route, data={**values, "csrf_token": token.decode()})

    def display_name(self):
        with self.app.app_context():
            return db.session.get(User, self.owner_id).display_name

    def test_report_form_preselects_only_the_requested_pet(self):
        page = self.client.get(f"/reports/new?pet_id={self.pet_id}").get_data(as_text=True)
        self.assertRegex(page, rf'value="{self.pet_id}"\s+checked')
        self.assertNotRegex(page, rf'value="{self.second_id}"\s+checked')

    def test_report_form_ignores_another_users_or_invalid_pet(self):
        for value in (self.foreign_id, "not-a-number"):
            page = self.client.get(f"/reports/new?pet_id={value}").get_data(as_text=True)
            self.assertNotIn("checked", page)
            self.assertNotIn("Hidden", page)

    def test_pet_page_links_to_preselected_report(self):
        page = self.client.get(f"/pets/{self.pet_id}").get_data(as_text=True)
        self.assertIn(f"/reports/new?pet_id={self.pet_id}", page)

    def test_settings_requires_login(self):
        response = self.app.test_client().get("/settings")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_settings_saves_display_name(self):
        response = self.post("/settings", {"display_name": "  New Name  "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.display_name(), "New Name")

    def test_settings_rejects_invalid_display_name(self):
        for value in ("   ", "x" * 51):
            response = self.post("/settings", {"display_name": value})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Enter a display name", response.data)
            self.assertEqual(self.display_name(), "Original")

    def test_settings_post_requires_csrf_token(self):
        response = self.client.post("/settings", data={"display_name": "Changed"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.display_name(), "Original")

    def test_settings_escapes_display_name(self):
        self.post("/settings", {"display_name": "<script>x</script>"})
        page = self.client.get("/settings")
        self.assertNotIn(b"<script>x</script>", page.data)


if __name__ == "__main__":
    unittest.main()
