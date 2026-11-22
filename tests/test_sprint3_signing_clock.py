"""Verify session and CSRF behavior around test-runner clock adjustments."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from extensions import db
from models import Contact, Report, ReportPet, User
from sprint3_base import PNG_BYTES, Sprint3TestCase


class SigningClockTests(Sprint3TestCase):
    def setUp(self):
        self.wall_time = Mock(return_value=1_800_000_000)
        self.elapsed = Mock(return_value=100)
        self.enterContext(patch("signing_clock.time", self.wall_time))
        self.enterContext(patch("signing_clock.monotonic", self.elapsed))
        self.enterContext(
            patch("itsdangerous.timed.time", SimpleNamespace(time=self.wall_time))
        )
        super().setUp()

    def roll_back_wall_clock(self):
        self.wall_time.return_value -= 2
        self.elapsed.return_value += 1

    def sign_in(self):
        response = self.login(self.owner)
        self.assertEqual(response.headers.get("Location"), "/pets")

    def submit_login(self, token):
        owner = self.users["owner"]
        return self.owner.post(
            "/login",
            data={
                "email": owner["email"],
                "password": owner["password"],
                "csrf_token": token,
            },
        )

    def test_login_form_survives_wall_clock_rollback(self):
        token = self.csrf(self.owner)
        self.roll_back_wall_clock()
        response = self.submit_login(token)
        self.assertEqual(response.headers.get("Location"), "/pets")

    def test_authenticated_get_survives_wall_clock_rollback(self):
        self.sign_in()
        self.roll_back_wall_clock()
        self.assertEqual(self.owner.get("/pets").status_code, 200)

    def test_pet_name_persists_after_wall_clock_rollback(self):
        self.sign_in()
        token = self.csrf(self.owner)
        self.roll_back_wall_clock()
        name = self.pets["special_straight"]["name"]
        response = self.owner.post(
            "/pets/new", data={"name": name, "species": "Cat", "csrf_token": token}
        )
        self.assertRegex(response.headers.get("Location", ""), r"^/pets/\d+$")
        pet_id = int(response.headers["Location"].rsplit("/", 1)[1])
        self.assertEqual(self.pet_snapshot(pet_id)["name"], name)

    def test_contact_saves_after_wall_clock_rollback(self):
        self.sign_in()
        address = "a" * 255
        values = self.contact_values("shelter_phone_only", address=address)
        values["csrf_token"] = self.csrf(self.owner)
        self.roll_back_wall_clock()
        response = self.owner.post("/contacts/new", data=values)
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(Contact.query.one().address, address)

    def test_settings_validation_survives_wall_clock_rollback(self):
        self.sign_in()
        token = self.csrf(self.owner)
        self.roll_back_wall_clock()
        response = self.owner.post(
            "/settings", data={"email": "updated@example.test", "csrf_token": token}
        )
        self.assertEqual(response.status_code, 200)
        self.assert_field_error(response, "current_password")
        self.assertEqual(self.user_value("owner", "email"), self.users["owner"]["email"])

    def test_resolved_photo_permissions_survive_wall_clock_rollback(self):
        self.login_both()
        photo_path = "uploads/resolved.png"
        (self.upload_dir / "resolved.png").write_bytes(PNG_BYTES)
        pet_id = self.seed_pet(photo_path=photo_path)
        with self.app.app_context():
            report = Report(
                owner_id=self.user_ids["owner"], status="found", is_shared=True
            )
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=pet_id))
            db.session.commit()
        self.roll_back_wall_clock()
        owner_photo = self.owner.get(f"/static/{photo_path}")
        with owner_photo:
            self.assertEqual(owner_photo.status_code, 200)
            self.assertEqual(owner_photo.data, PNG_BYTES)
        self.assertEqual(self.other.get(f"/static/{photo_path}").status_code, 404)

    def test_session_does_not_expire_early_after_wall_clock_jump(self):
        self.app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=3)
        self.sign_in()
        self.wall_time.return_value += 60
        self.elapsed.return_value += 2
        self.assertEqual(self.owner.get("/pets").status_code, 200)

    def test_csrf_does_not_expire_early_after_wall_clock_jump(self):
        self.app.config["WTF_CSRF_TIME_LIMIT"] = 3
        token = self.csrf(self.owner)
        self.wall_time.return_value += 60
        self.elapsed.return_value += 2
        self.assertEqual(self.submit_login(token).headers.get("Location"), "/pets")

    def test_session_still_expires_after_elapsed_time(self):
        self.app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=3)
        self.sign_in()
        self.elapsed.return_value += 4
        self.assert_redirects_to_login(self.owner.get("/pets"))

    def test_csrf_still_expires_after_elapsed_time(self):
        self.app.config["WTF_CSRF_TIME_LIMIT"] = 3
        token = self.csrf(self.owner)
        self.elapsed.return_value += 4
        response = self.submit_login(token)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"CSRF token has expired", response.data)

    def test_revoked_session_still_fails_after_wall_clock_rollback(self):
        self.sign_in()
        with self.app.app_context():
            user = db.session.get(User, self.user_ids["owner"])
            user.session_version += 1
            db.session.commit()
        self.roll_back_wall_clock()
        self.assert_redirects_to_login(self.owner.get("/pets"))
