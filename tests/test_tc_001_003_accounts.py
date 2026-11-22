"""TC-001 to TC-003 and TC-1002: registration, login, logout, sessions, safe redirects."""

import unittest
from urllib.parse import urlsplit

from extensions import db
from models import User
from sprint3_base import Sprint3TestCase

NEW_EMAIL = "new.household@example.test"
NEW_PASSWORD = "SyntheticPass301!"


class AccountTests(Sprint3TestCase):
    def user_count(self):
        with self.app.app_context():
            return User.query.count()

    def register(self, client, email=NEW_EMAIL, password=NEW_PASSWORD, confirm=None):
        return self.post(client, "/register", {
            "email": email, "password": password,
            "confirm_password": password if confirm is None else confirm,
        })

    def test_tc_001_register_then_login_opens_pet_list(self):
        response = self.register(self.guest)
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNotNone(User.query.filter_by(email=NEW_EMAIL).first())
        self.logout(self.guest)
        client = self.app.test_client()
        response = self.post(client, "/login", {"email": NEW_EMAIL, "password": NEW_PASSWORD},
                             follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request.path, "/pets")

    def test_tc_002_invalid_registration_shows_error_and_creates_nothing(self):
        used = self.users["owner"]["email"]
        cases = [
            ("", NEW_PASSWORD, None, "Email is required."),
            ("bad-email", NEW_PASSWORD, None, "Enter a valid email address."),
            (used, NEW_PASSWORD, None, "An account with this email already exists."),
            (NEW_EMAIL, "", "", "Password is required."),
            (NEW_EMAIL, "short", None, "at least 8 characters"),
            (NEW_EMAIL, NEW_PASSWORD, "Different301!", "Passwords do not match."),
        ]
        before = self.user_count()
        for email, password, confirm, message in cases:
            with self.subTest(message=message):
                client = self.app.test_client()
                response = self.register(client, email, password, confirm)
                self.assertEqual(response.status_code, 200)
                self.assertIn(message, self.page_text(response))
                self.assertEqual(self.user_count(), before)
                self.assert_redirects_to_login(client.get("/pets"))

    def test_tc_002_wrong_login_password_shows_error_without_session(self):
        response = self.login(self.guest, "owner", password="WrongPass999!")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid email or password.", self.page_text(response))
        self.assert_redirects_to_login(self.guest.get("/pets"))

    def test_tc_003_logout_blocks_saved_private_pages(self):
        pet_id = self.seed_pet(name="Private Biscuit")
        self.login(self.owner)
        self.assertEqual(self.owner.get(f"/pets/{pet_id}").status_code, 200)
        self.assertEqual(self.logout(self.owner).status_code, 302)
        for route in ("/pets", f"/pets/{pet_id}"):
            for _refresh in range(2):
                response = self.owner.get(route)
                self.assert_redirects_to_login(response)
                self.assertNotIn(b"Private Biscuit", response.data)

    def test_tc_1002_private_routes_reject_signed_out_requests(self):
        pet_id = self.seed_pet()
        contact_id = self.seed_contact("vet_full")
        for route in ("/pets", "/pets/new", f"/pets/{pet_id}", f"/pets/{pet_id}/edit",
                      "/contacts", "/contacts/new", f"/contacts/{contact_id}", "/reports",
                      "/reports/new", "/settings"):
            with self.subTest(route=route):
                self.assert_redirects_to_login(self.guest.get(route))

    def test_tc_1002_sign_in_and_sign_out_control_the_session(self):
        self.assert_redirects_to_login(self.owner.get("/settings"))
        self.login(self.owner)
        self.assertEqual(self.owner.get("/settings").status_code, 200)
        self.assertEqual(self.owner.get("/logout").status_code, 405)
        self.assertEqual(self.owner.get("/settings").status_code, 200)
        self.logout(self.owner)
        self.assert_redirects_to_login(self.owner.get("/settings"))

    def test_tc_1002_logout_requires_csrf_token(self):
        self.login(self.owner)
        self.assertEqual(self.owner.post("/logout").status_code, 400)
        self.assertEqual(self.owner.get("/settings").status_code, 200)

    def test_login_redirect_accepts_same_site_paths(self):
        for target in self.invalid["safe_next"]:
            with self.subTest(target=target):
                client = self.app.test_client()
                response = self.login(client, next_url=target)
                self.assertEqual(response.status_code, 302)
                location = urlsplit(response.headers["Location"])
                actual = location.path + (f"?{location.query}" if location.query else "")
                self.assertEqual(actual, target)
                self.assertIn(location.netloc, ("", "localhost"))

    def test_login_redirect_rejects_unsafe_targets(self):
        for target in self.invalid["unsafe_next"]:
            with self.subTest(target=target):
                client = self.app.test_client()
                response = self.login(client, next_url=target)
                self.assertEqual(response.status_code, 302)
                location = urlsplit(response.headers["Location"])
                self.assertEqual(location.path, "/pets")
                self.assertIn(location.netloc, ("", "localhost"))


if __name__ == "__main__":
    unittest.main()
