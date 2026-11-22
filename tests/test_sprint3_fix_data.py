"""Regression tests for patch contract items P5, P6, P7, and P10 (settings, data, seed)."""

import hashlib
import re
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from sqlalchemy import text

import settings
from extensions import db
from models import PasswordResetToken, Pet, Report, ReportComment, ReportPet, User, format_measure
from sprint3_base import Sprint3TestCase

EMAIL_TAKEN = "An account with this email already exists."
RIVAL_EMAIL = "rival-claim@example.test"
SMALL = "0.00001"
COMMENT = "Synthetic sighting near the park."


class P5ConcurrentEmailChangeTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        # Show an unhandled error as the 500 a real user would get.
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        self.assertEqual(self.login(self.owner).status_code, 302)
        with self.app.app_context():
            db.session.add(PasswordResetToken(
                user_id=self.user_ids["owner"],
                token_hash=hashlib.sha256(b"p5-unused-token").hexdigest(),
                expires_at=datetime.utcnow() + timedelta(hours=1)))
            db.session.commit()

    def change_email_while_rival_claims_it(self):
        """Commit the rival row after validation, just before the autoflushing query."""
        real_invalidate = settings.invalidate_reset_tokens

        def claim_then_invalidate(user_id):
            with db.engine.begin() as connection:
                connection.execute(
                    text("INSERT INTO users (email, password_hash, session_version, created_at) "
                         "VALUES (:email, 'synthetic-hash', 1, :now)"),
                    {"email": RIVAL_EMAIL, "now": datetime.utcnow()})
            return real_invalidate(user_id)

        with mock.patch.object(settings, "invalidate_reset_tokens", claim_then_invalidate):
            return self.post(self.owner, "/settings", {
                "display_name": "", "full_name": "", "phone": "", "email": RIVAL_EMAIL,
                "current_password": self.users["owner"]["password"],
            })

    def test_p5_autoflush_conflict_shows_inline_email_error(self):
        response = self.change_email_while_rival_claims_it()
        self.assertEqual(response.status_code, 200)
        self.assertIn(EMAIL_TAKEN, self.page_text(response))
        self.assert_field_error(response, "email")

    def test_p5_conflict_rolls_back_user_and_tokens(self):
        self.change_email_while_rival_claims_it()
        self.assertEqual(self.user_value("owner", "email"), self.users["owner"]["email"])
        with self.app.app_context():
            token = PasswordResetToken.query.filter_by(user_id=self.user_ids["owner"]).one()
            self.assertIsNone(token.used_at)

    def test_p5_session_is_usable_after_conflict(self):
        self.change_email_while_rival_claims_it()
        response = self.owner.get("/settings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.control_value(response, "email"), self.users["owner"]["email"])


class P6SmallMeasurementTests(Sprint3TestCase):
    def test_p6_format_never_uses_exponent_and_round_trips(self):
        for value in (0.00001, 0.000001, 1.5e-05, 1.234e-07, 0.0001, 5e-324):
            with self.subTest(value=value):
                shown = format_measure(value)
                self.assertRegex(shown, r"^\d+(\.\d+)?$")
                self.assertEqual(float(shown), value)

    def test_p6_large_values_do_not_use_exponent(self):
        for value in (1e16, 1e22):
            with self.subTest(value=value):
                shown = format_measure(value)
                self.assertRegex(shown, r"^\d+$")
                self.assertEqual(float(shown), value)

    def test_p6_normal_values_keep_existing_output(self):
        cases = ((23.75, "23.75"), (10, "10"), (10.0, "10"), (0.5, "0.5"), (120.0, "120"),
                 (0.1, "0.1"), (None, ""))
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(format_measure(value), expected)

    def test_p6_small_value_prefills_and_survives_unrelated_edit(self):
        self.assertEqual(self.login(self.owner).status_code, 302)
        created = self.post(self.owner, "/pets/new", self.pet_values(
            "full_profile", height_inches=SMALL, weight_lbs=SMALL))
        self.assertEqual(created.status_code, 302)
        pet_id = int(created.headers["Location"].rsplit("/", 1)[-1])

        form = self.owner.get(f"/pets/{pet_id}/edit")
        self.assertEqual(self.control_value(form, "height_inches"), SMALL)
        self.assertEqual(self.control_value(form, "weight_lbs"), SMALL)

        saved = self.post(self.owner, f"/pets/{pet_id}/edit", self.pet_values(
            "full_profile", name="Renamed Synthetic Pet",
            height_inches=self.control_value(form, "height_inches"),
            weight_lbs=self.control_value(form, "weight_lbs")))
        self.assertEqual(saved.status_code, 302)
        with self.app.app_context():
            pet = db.session.get(Pet, pet_id)
            self.assertEqual(pet.name, "Renamed Synthetic Pet")
            self.assertEqual(pet.height_inches, 0.00001)
            self.assertEqual(pet.weight_lbs, 0.00001)

    def test_p6_detail_page_shows_plain_decimal(self):
        self.assertEqual(self.login(self.owner).status_code, 302)
        pet_id = self.seed_pet(height_inches=0.00001, weight_lbs=0.00001)
        text_shown = self.page_text(self.owner.get(f"/pets/{pet_id}"))
        self.assertIn(f"{SMALL} in", text_shown)
        self.assertIn(f"{SMALL} lb", text_shown)
        self.assertNotIn("1e-05", text_shown)


class P7CommentDeletionTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.login_both()
        self.report_id = self.make_report("First Synthetic Pet")
        self.second_report_id = self.make_report("Second Synthetic Pet")
        self.post_url = f"/community/reports/{self.report_id}"
        with self.app.app_context():
            comment = ReportComment(report_id=self.report_id, author_id=self.user_ids["other"],
                                    body=COMMENT)
            db.session.add(comment)
            db.session.commit()
            self.comment_id = comment.id
        self.delete_url = f"{self.post_url}/comments/{self.comment_id}/delete"

    def make_report(self, pet_name):
        pet_id = self.seed_pet(name=pet_name)
        with self.app.app_context():
            report = Report(owner_id=self.user_ids["owner"], status="open", is_shared=True,
                            shared_at=datetime.utcnow(), latitude=33.21, longitude=-97.13,
                            community_area="North Park",
                            community_description="Please share sightings.")
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=pet_id))
            db.session.commit()
            return report.id

    def unshare(self):
        response = self.post(self.owner, f"{self.post_url}/unshare")
        self.assertEqual(response.status_code, 302)

    def comment_exists(self):
        with self.app.app_context():
            return db.session.get(ReportComment, self.comment_id) is not None

    def pending_flash_categories(self, client):
        with client.session_transaction() as session:
            return [category for category, _message in session.get("_flashes", [])]

    def test_p7_author_can_delete_while_shared_and_returns_to_post(self):
        response = self.post(self.other, self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.post_url, response.headers["Location"])
        self.assertFalse(self.comment_exists())

    def test_p7_author_can_delete_after_unshare_and_returns_to_feed(self):
        self.unshare()
        response = self.post(self.other, self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertRegex(response.headers["Location"], r"/community/?(\?.*)?$")
        self.assertFalse(self.comment_exists())
        self.assertIn("success", self.pending_flash_categories(self.other))
        self.assertEqual(self.other.get(response.headers["Location"]).status_code, 200)

    def test_p7_report_owner_cannot_delete_others_comment_after_unshare(self):
        self.unshare()
        self.assertEqual(self.post(self.owner, self.delete_url).status_code, 404)
        self.assertTrue(self.comment_exists())

    def test_p7_wrong_report_id_is_404_after_unshare(self):
        self.unshare()
        route = f"/community/reports/{self.second_report_id}/comments/{self.comment_id}/delete"
        self.assertEqual(self.post(self.other, route).status_code, 404)
        self.assertTrue(self.comment_exists())

    def test_p7_missing_comment_is_404_after_unshare(self):
        self.unshare()
        route = f"{self.post_url}/comments/{self.comment_id + 999}/delete"
        self.assertEqual(self.post(self.other, route).status_code, 404)

    def test_p7_guest_cannot_delete_after_unshare(self):
        self.unshare()
        self.assert_redirects_to_login(self.post(self.guest, self.delete_url))
        self.assertTrue(self.comment_exists())

    def test_p7_unsharing_still_hides_post_and_comments(self):
        with self.app.app_context():
            stranger = User(email="p7-stranger@example.test")
            stranger.set_password("SyntheticStranger123!")
            db.session.add(stranger)
            db.session.commit()
        viewer = self.app.test_client()
        signed_in = self.post(viewer, "/login", {
            "email": "p7-stranger@example.test", "password": "SyntheticStranger123!"})
        self.assertEqual(signed_in.status_code, 302)
        self.unshare()
        search = {"latitude": "33.21", "longitude": "-97.13", "radius": "10"}
        for client in (self.other, viewer):
            self.assertEqual(client.get(self.post_url).status_code, 404)
            feed = client.get("/community", query_string=search)
            self.assertEqual(feed.status_code, 200)
            page = self.page_text(feed)
            self.assertNotIn("First Synthetic Pet", page)
            self.assertIn("Second Synthetic Pet", page)
        # The author may see their own retained comment (P7 entry point); nobody else may.
        self.assertNotIn(COMMENT, self.page_text(viewer.get("/community", query_string=search)))


class P7EntryPointTests(Sprint3TestCase):
    TITLE = "Your comments on unshared reports"
    MY_COMMENT = "Entry point comment by the author."
    OWNER_COMMENT = "Entry point reply by the report owner."
    PRIVATE = {
        "pet_name": "Zephyrine",
        "pet_breed": "Synthetic Longhair",
        "photo": "p7-private-photo.png",
        "area": "Quillfeather Heights",
        "description": "Marigold collar description.",
        "location": "Private Tamarack Lane",
        "report_notes": "Private report note text.",
        "latitude": "33.2177",
        "longitude": "-97.1388",
        "owner_name": "Ottoline Report Owner",
    }

    def setUp(self):
        super().setUp()
        self.login_both()
        pet_id = self.seed_pet(name=self.PRIVATE["pet_name"], breed=self.PRIVATE["pet_breed"],
                               photo_path=f"uploads/{self.PRIVATE['photo']}")
        with self.app.app_context():
            db.session.get(User, self.user_ids["owner"]).display_name = self.PRIVATE["owner_name"]
            third = User(email="third-household@example.test")
            third.set_password("SyntheticThird123!")
            db.session.add(third)
            report = Report(owner_id=self.user_ids["owner"], status="open", is_shared=False,
                            shared_at=datetime(2026, 3, 1), latitude=33.2177, longitude=-97.1388,
                            community_area=self.PRIVATE["area"],
                            community_description=self.PRIVATE["description"],
                            last_seen_location=self.PRIVATE["location"],
                            notes=self.PRIVATE["report_notes"])
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=pet_id))
            mine = ReportComment(report_id=report.id, author_id=self.user_ids["other"],
                                 body=self.MY_COMMENT, created_at=datetime(2026, 3, 14, 9, 26))
            theirs = ReportComment(report_id=report.id, author_id=self.user_ids["owner"],
                                   body=self.OWNER_COMMENT,
                                   created_at=datetime(2026, 3, 15, 10, 0))
            db.session.add_all([mine, theirs])
            db.session.commit()
            self.report_id, self.comment_id = report.id, mine.id
        self.post_url = f"/community/reports/{self.report_id}"
        self.delete_url = f"{self.post_url}/comments/{self.comment_id}/delete"
        self.third = self.app.test_client()
        signed_in = self.post(self.third, "/login", {
            "email": "third-household@example.test", "password": "SyntheticThird123!"})
        self.assertEqual(signed_in.status_code, 302)

    def feed(self, client, **query):
        response = client.get("/community", query_string=query)
        self.assertEqual(response.status_code, 200)
        return response

    def delete_form(self, response):
        html = response.get_data(as_text=True)
        pattern = rf'<form\b[^>]*\baction="{re.escape(self.delete_url)}"[^>]*>(.*?)</form>'
        match = re.search(pattern, html, re.DOTALL)
        self.assertIsNotNone(match, "no form posts to the existing delete route")
        self.assertRegex(match.group(0).split(">", 1)[0].lower(), r'method="post"')
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', match.group(1))
        self.assertIsNotNone(token, "delete form has no CSRF token")
        return token.group(1)

    def comment_exists(self):
        with self.app.app_context():
            return db.session.get(ReportComment, self.comment_id) is not None

    def test_p7_entry_author_sees_section_comment_and_date(self):
        text_shown = self.page_text(self.feed(self.other))
        self.assertIn(self.TITLE, text_shown)
        self.assertIn(self.MY_COMMENT, text_shown)
        self.assertIn("2026-03-14", text_shown)

    def test_p7_entry_delete_button_works_with_page_csrf_token(self):
        token = self.delete_form(self.feed(self.other))
        response = self.other.post(self.delete_url, data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.comment_exists())

    def test_p7_entry_delete_requires_csrf_token(self):
        self.delete_form(self.feed(self.other))
        response = self.other.post(self.delete_url, data={})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(self.comment_exists())

    def test_p7_entry_section_exposes_no_report_details(self):
        pages = {
            "plain": self.feed(self.other),
            "search": self.feed(self.other, latitude="40.5", longitude="-100.5", radius="10"),
        }
        for page_name, response in pages.items():
            text_shown = self.page_text(response)
            for field, value in self.PRIVATE.items():
                with self.subTest(page=page_name, field=field):
                    self.assertNotIn(value, text_shown)
            with self.subTest(page=page_name, field="other_comment"):
                self.assertNotIn(self.OWNER_COMMENT, text_shown)
            with self.subTest(page=page_name, field="owner_email"):
                self.assertNotIn(self.users["owner"]["email"], text_shown)

    def test_p7_entry_user_without_retained_comment_sees_no_section(self):
        text_shown = self.page_text(self.feed(self.third))
        self.assertNotIn(self.TITLE, text_shown)
        self.assertNotIn(self.MY_COMMENT, text_shown)
        self.assertNotIn(self.OWNER_COMMENT, text_shown)

    def test_p7_entry_other_author_sees_only_their_own_comment(self):
        response = self.feed(self.owner)
        text_shown = self.page_text(response)
        self.assertIn(self.OWNER_COMMENT, text_shown)
        self.assertNotIn(self.MY_COMMENT, text_shown)
        self.assertNotIn(self.delete_url, response.get_data(as_text=True))

    def test_p7_entry_guest_is_sent_to_login(self):
        self.assert_redirects_to_login(self.guest.get("/community"))

    def test_p7_entry_section_disappears_when_report_is_shared_again(self):
        self.assertIn(self.TITLE, self.page_text(self.feed(self.other)))
        shared = self.post(self.owner, f"{self.post_url}/share", {
            "display_name": self.PRIVATE["owner_name"],
            "community_area": self.PRIVATE["area"],
            "community_description": self.PRIVATE["description"],
            "latitude": self.PRIVATE["latitude"],
            "longitude": self.PRIVATE["longitude"],
            "confirm_sharing": "yes",
        })
        self.assertEqual(shared.status_code, 302)
        self.assertNotIn(self.TITLE, self.page_text(self.feed(self.other)))
        self.assertTrue(self.comment_exists())

    def test_p7_entry_section_disappears_after_comment_is_deleted(self):
        token = self.delete_form(self.feed(self.other))
        response = self.other.post(self.delete_url, data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)
        text_shown = self.page_text(self.other.get(response.headers["Location"]))
        self.assertNotIn(self.TITLE, text_shown)
        self.assertNotIn(self.MY_COMMENT, text_shown)


class P10SeedPrerequisiteTests(Sprint3TestCase):
    SPRINT3_COLUMNS = ("sex", "height_inches", "weight_lbs", "colors", "markings",
                       "microchip_status", "microchip_number")
    BASE_COLUMNS = (
        "id INTEGER PRIMARY KEY", "owner_id INTEGER NOT NULL", "name VARCHAR(100) NOT NULL",
        "species VARCHAR(50) NOT NULL", "breed VARCHAR(100)", "birth_date DATE", "notes TEXT",
        "photo_path VARCHAR(255)", "photo_uploaded_at DATETIME", "created_at DATETIME NOT NULL",
        "updated_at DATETIME NOT NULL",
    )
    TYPES = {"sex": "VARCHAR(20)", "height_inches": "FLOAT", "weight_lbs": "FLOAT",
             "colors": "VARCHAR(100)", "markings": "VARCHAR(255)",
             "microchip_status": "VARCHAR(20)", "microchip_number": "VARCHAR(15)"}

    def rebuild_pets_without(self, missing):
        kept = [f"{name} {self.TYPES[name]}" for name in self.SPRINT3_COLUMNS
                if name not in missing]
        with self.app.app_context():
            with db.engine.begin() as connection:
                connection.execute(text("DROP TABLE pets"))
                connection.execute(text(
                    f"CREATE TABLE pets ({', '.join(self.BASE_COLUMNS + tuple(kept))})"))

    def counts(self):
        with self.app.app_context():
            return {
                "users": db.session.execute(text("SELECT COUNT(*) FROM users")).scalar(),
                "pets": db.session.execute(text("SELECT COUNT(*) FROM pets")).scalar(),
                "reports": db.session.execute(text("SELECT COUNT(*) FROM reports")).scalar(),
                "comments": db.session.execute(
                    text("SELECT COUNT(*) FROM report_comments")).scalar(),
            }

    def assert_blocked_without_partial_seed(self):
        before = self.counts()
        result = self.app.test_cli_runner().invoke(args=["seed-community-demo"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("flask upgrade-community", result.output)
        self.assertIn("flask upgrade-sprint3", result.output)
        self.assertEqual(self.counts(), before)
        self.assertEqual(list(Path(self.app.config["UPLOAD_FOLDER"]).iterdir()), [])

    def test_p10_help_names_both_upgrade_commands(self):
        result = self.app.test_cli_runner().invoke(args=["seed-community-demo", "--help"])
        self.assertEqual(result.exit_code, 0)
        output = re.sub(r"\s+", " ", result.output)
        self.assertIn("flask upgrade-community", output)
        self.assertIn("flask upgrade-sprint3", output)

    def test_p10_all_sprint3_pet_columns_missing(self):
        self.rebuild_pets_without(set(self.SPRINT3_COLUMNS))
        self.assert_blocked_without_partial_seed()

    def test_p10_each_single_missing_column_is_detected(self):
        for column in self.SPRINT3_COLUMNS:
            with self.subTest(column=column):
                self.rebuild_pets_without({column})
                self.assert_blocked_without_partial_seed()


if __name__ == "__main__":
    unittest.main()
