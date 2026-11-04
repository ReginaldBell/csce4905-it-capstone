"""Run: python -m unittest discover -s tests -v (with src on PYTHONPATH)."""

import os
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "community-tests-only")

from app import create_app
from community import _distance_miles
from config import Config
from extensions import db
from models import Contact, Pet, Report, ReportComment, ReportPet, User


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "COMMUNITY_TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    WTF_CSRF_ENABLED = True


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.app = create_app(TestConfig)
        self.app.static_folder = self.files.name
        self.app.config["UPLOAD_FOLDER"] = str(Path(self.files.name) / "uploads")
        Path(self.app.config["UPLOAD_FOLDER"]).mkdir()
        with self.app.app_context():
            db.create_all()
            owner = User(email="private-owner@example.com")
            neighbor = User(email="neighbor@example.com")
            stranger = User(email="stranger@example.com")
            for user in (owner, neighbor, stranger):
                user.set_password("DemoPass123!")
            db.session.add_all([owner, neighbor, stranger])
            db.session.flush()
            self.owner_id, self.neighbor_id = owner.id, neighbor.id
            pet = Pet(
                owner_id=owner.id,
                name="Luna",
                species="Dog",
                breed="Mix",
                notes="PRIVATE PET NOTES",
                photo_path="uploads/luna.png",
            )
            report = Report(
                owner_id=owner.id,
                status="open",
                last_seen_location="PRIVATE STREET ADDRESS",
                notes="PRIVATE REPORT NOTES",
            )
            db.session.add_all([pet, report])
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=pet.id))
            db.session.commit()
            self.pet_id, self.report_id = pet.id, report.id
        (Path(self.app.config["UPLOAD_FOLDER"]) / "luna.png").write_bytes(
            b"photo fixture"
        )
        self.owner = self.app.test_client()
        self.neighbor = self.app.test_client()
        self.stranger = self.app.test_client()
        self.guest = self.app.test_client()
        for client, email in [
            (self.owner, "private-owner@example.com"),
            (self.neighbor, "neighbor@example.com"),
            (self.stranger, "stranger@example.com"),
        ]:
            self.post(
                client, "/login", {"email": email, "password": "DemoPass123!"}, "/login"
            )
        self.post_url = f"/community/reports/{self.report_id}"

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.files.cleanup()

    def post(self, client, route, values=None, token_route="/pets"):
        page = client.get(token_route)
        token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
        self.assertIsNotNone(token, token_route)
        data = dict(values or {})
        data["csrf_token"] = token.group(1).decode()
        return client.post(route, data=data)

    def share(self, **changes):
        values = dict(
            display_name="Luna's owner",
            community_area="North Park",
            community_description="Blue collar. Please share sightings.",
            latitude="33.21",
            longitude="-97.13",
            confirm_sharing="yes",
        )
        values.update(changes)
        return self.post(self.owner, self.post_url + "/share", values)

    def search(self, client=None, **changes):
        values = dict(latitude="33.21", longitude="-97.13", radius="10")
        values.update(changes)
        return (client or self.neighbor).get("/community", query_string=values)

    def comment(self, client=None, **changes):
        values = dict(display_name="Helpful neighbor", body="I saw Luna near the park.")
        values.update(changes)
        return self.post(client or self.neighbor, self.post_url + "/comments", values)

    def test_private_by_default_and_owner_only_sharing(self):
        self.assertEqual(self.neighbor.get(self.post_url).status_code, 404)
        self.assertNotIn(b"Luna", self.search().data)
        self.assertEqual(self.neighbor.get(self.post_url + "/share").status_code, 404)
        self.assertEqual(
            self.post(self.neighbor, self.post_url + "/share", {}).status_code, 404
        )
        self.assertEqual(
            self.post(self.neighbor, self.post_url + "/unshare").status_code, 404
        )
        self.assertEqual(self.share().status_code, 302)
        self.assertEqual(self.neighbor.get(self.post_url).status_code, 200)
        self.assertEqual(
            self.neighbor.get(f"/reports/{self.report_id}").status_code, 404
        )
        self.assertEqual(self.neighbor.get(f"/pets/{self.pet_id}").status_code, 404)

    def test_only_selected_public_fields_are_shown_and_escaped(self):
        self.share(community_description="<script>alert('x')</script>")
        for response in [self.search(), self.neighbor.get(self.post_url)]:
            for private in [
                b"PRIVATE STREET",
                b"PRIVATE PET NOTES",
                b"PRIVATE REPORT NOTES",
                b"private-owner@example.com",
            ]:
                self.assertNotIn(private, response.data)
            self.assertIn(b"&lt;script&gt;", response.data)
            self.assertNotIn(b"<script>alert", response.data)

    def test_share_requires_confirmation_valid_fields_and_coordinates(self):
        for changes in [
            dict(confirm_sharing=""),
            dict(latitude="nan"),
            dict(longitude="inf"),
            dict(latitude="91"),
            dict(longitude="-181"),
            dict(latitude=""),
            dict(display_name=""),
            dict(community_area="x" * 121),
            dict(community_description="x" * 1001),
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(self.share(**changes).status_code, 200)
                with self.app.app_context():
                    self.assertFalse(db.session.get(Report, self.report_id).is_shared)
        self.assertEqual(self.share(latitude="0", longitude="0").status_code, 302)

    def test_distance_filter_and_radius_validation(self):
        self.share()
        self.assertIn(b"Luna", self.search().data)
        self.assertNotIn(b"Luna", self.search(latitude="35", longitude="-100").data)
        for value in ["nan", "inf", "-91", ""]:
            self.assertIn(b"field-error", self.search(latitude=value).data)
        for changes in [
            dict(radius="11"),
            dict(radius="text"),
            dict(page="0"),
            dict(page="text"),
        ]:
            self.assertIn(b"field-error", self.search(**changes).data)
        self.assertAlmostEqual(_distance_miles(0, 0, 0, 1), 69.09, places=1)
        self.assertLess(_distance_miles(0, 179.99, 0, -179.99), 2)
        self.assertEqual(_distance_miles(33, -97, 33, -97), 0)

    def test_nearest_first_and_load_more(self):
        self.share()
        with self.app.app_context():
            for i in range(12):
                pet = Pet(owner_id=self.owner_id, name=f"FeedPet{i}", species="Cat")
                report = Report(
                    owner_id=self.owner_id,
                    status="open",
                    is_shared=True,
                    latitude=33.22 + i * 0.001,
                    longitude=-97.13,
                    community_area="Park",
                    community_description="Missing cat",
                    shared_at=datetime.utcnow(),
                )
                db.session.add_all([pet, report])
                db.session.flush()
                db.session.add(ReportPet(report_id=report.id, pet_id=pet.id))
            db.session.commit()
        first = self.search().get_data(as_text=True)
        self.assertEqual(first.count('class="community-post"'), 10)
        self.assertLess(first.index("Luna"), first.index("FeedPet0"))
        self.assertIn("Load more reports", first)
        second = self.search(page="2").get_data(as_text=True)
        self.assertEqual(second.count('class="community-post"'), 13)
        self.assertNotIn("Load more reports", second)

    def test_comments_owner_replies_and_author_only_deletion(self):
        self.share()
        self.assertEqual(self.comment(author_id=str(self.owner_id)).status_code, 302)
        self.assertEqual(
            self.comment(
                self.owner, display_name="Luna's owner", body="Thank you!"
            ).status_code,
            302,
        )
        with self.app.app_context():
            comment = ReportComment.query.order_by(ReportComment.id).first()
            comment_id = comment.id
            self.assertEqual(comment.author_id, self.neighbor_id)
        page = self.neighbor.get(self.post_url)
        self.assertIn(b"I saw Luna", page.data)
        self.assertIn(b"Thank you!", page.data)
        self.assertIn(b"Report owner", page.data)
        route = self.post_url + f"/comments/{comment_id}/delete"
        self.assertEqual(self.post(self.stranger, route).status_code, 404)
        self.assertEqual(self.post(self.owner, route).status_code, 404)
        self.assertEqual(self.post(self.neighbor, route).status_code, 302)
        self.assertNotIn(b"I saw Luna", self.neighbor.get(self.post_url).data)

    def test_invalid_comments_do_not_save_or_change_display_name(self):
        self.share()
        for changes in [
            dict(body=" "),
            dict(body="x" * 1001),
            dict(display_name=""),
            dict(display_name="x" * 51),
        ]:
            self.assertEqual(self.comment(**changes).status_code, 200)
        with self.app.app_context():
            self.assertEqual(ReportComment.query.count(), 0)
            self.assertIsNone(db.session.get(User, self.neighbor_id).display_name)

    def test_comment_html_is_escaped(self):
        self.share()
        self.comment(body='<img src=x onerror="alert(1)">')
        response = self.neighbor.get(self.post_url)
        self.assertIn(b"&lt;img", response.data)
        self.assertNotIn(b"<img src=x", response.data)

    def test_resolved_posts_leave_feed_and_stop_new_comments(self):
        self.share()
        self.comment()
        for status in ["found", "closed"]:
            response = self.post(
                self.owner, f"/reports/{self.report_id}/status", {"status": status}
            )
            self.assertEqual(response.status_code, 302)
            self.assertNotIn(b"Luna", self.search().data)
            self.assertIn(b"I saw Luna", self.neighbor.get(self.post_url).data)
            self.assertEqual(self.comment(body="New sighting").status_code, 302)
        with self.app.app_context():
            self.assertEqual(ReportComment.query.count(), 1)
        self.assertEqual(self.share().status_code, 200)

    def test_unsharing_hides_post_comments_and_photos(self):
        self.share()
        self.comment()
        self.assertEqual(
            self.post(self.owner, self.post_url + "/unshare").status_code, 302
        )
        self.assertEqual(self.neighbor.get(self.post_url).status_code, 404)
        self.assertEqual(self.comment().status_code, 404)
        self.assertNotIn(b"Luna", self.search().data)
        self.assertEqual(self.neighbor.get("/static/uploads/luna.png").status_code, 404)

    def test_photo_access_follows_owner_and_sharing(self):
        path = "/static/uploads/luna.png"
        with self.owner.get(path) as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.neighbor.get(path).status_code, 404)
        self.assertEqual(self.guest.get(path).status_code, 302)
        self.share()
        with self.neighbor.get(path) as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.guest.get(path).status_code, 302)

    def test_deleted_pet_does_not_leave_a_broken_feed_post(self):
        self.share()
        self.assertEqual(
            self.post(self.owner, f"/pets/{self.pet_id}/delete").status_code, 302
        )
        self.assertNotIn(b"Luna", self.search().data)
        self.assertEqual(self.neighbor.get(self.post_url).status_code, 404)

    def test_csrf_and_login_protect_community_actions(self):
        self.share()
        for route, values in [
            (self.post_url + "/share", {}),
            (self.post_url + "/unshare", {}),
            (self.post_url + "/comments", {"display_name": "A", "body": "Hi"}),
        ]:
            self.assertEqual(self.owner.post(route, data=values).status_code, 400)
        for path in ["/community", self.post_url, self.post_url + "/share"]:
            self.assertEqual(self.guest.get(path).status_code, 302)

    def test_existing_pet_contact_report_and_output_flows_still_work(self):
        pet_data = {
            "name": "Milo",
            "species": "Cat",
            "breed": "Mix",
            "notes": "Friendly",
        }
        self.assertEqual(self.post(self.owner, "/pets/new", pet_data).status_code, 302)
        self.assertEqual(
            self.post(
                self.owner, f"/pets/{self.pet_id}/edit", dict(pet_data, name="Luna")
            ).status_code,
            302,
        )
        response = self.post(
            self.owner,
            "/contacts/new",
            {
                "name": "Shelter",
                "category": "Animal Shelter",
                "email": "help@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        contact_id = int(response.location.rsplit("/", 1)[-1])
        response = self.post(
            self.owner,
            "/reports/new",
            {"pet_ids": str(self.pet_id), "last_seen_location": "Park"},
        )
        self.assertEqual(response.status_code, 302)
        report_id = int(response.location.rsplit("/", 1)[-1])
        for path in [
            f"/reports/{report_id}/email/{contact_id}",
            f"/reports/{report_id}/phone-script/{contact_id}",
            f"/reports/{report_id}/social-post",
            f"/reports/{report_id}/flyer",
        ]:
            self.assertEqual(self.owner.get(path).status_code, 200)
        self.assertEqual(self.post(self.owner, "/logout").status_code, 302)
        self.assertEqual(self.owner.get("/pets").status_code, 302)


class CommunityUpgradeTests(unittest.TestCase):
    def test_upgrade_keeps_existing_records_and_can_run_twice(self):
        app = create_app(TestConfig)
        with app.app_context():
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255), password_hash VARCHAR(255), created_at TIMESTAMP)"
                )
                connection.exec_driver_sql(
                    "CREATE TABLE reports (id INTEGER PRIMARY KEY, owner_id INTEGER, status VARCHAR(20), last_seen_at TIMESTAMP, last_seen_location VARCHAR(255), notes TEXT, created_at TIMESTAMP, updated_at TIMESTAMP, closed_at TIMESTAMP)"
                )
                connection.exec_driver_sql(
                    "INSERT INTO users (id, email, password_hash) VALUES (1, 'kept@example.com', 'existing-hash')"
                )
                connection.exec_driver_sql(
                    "INSERT INTO reports (id, owner_id, status, notes) VALUES (1, 1, 'open', 'Keep this note')"
                )
        runner = app.test_cli_runner()
        for _ in range(2):
            result = runner.invoke(args=["upgrade-community"])
            self.assertEqual(
                result.exit_code, 0, result.output + repr(result.exception)
            )
        with app.app_context():
            self.assertEqual(db.session.get(User, 1).email, "kept@example.com")
            report = db.session.get(Report, 1)
            self.assertEqual(report.notes, "Keep this note")
            self.assertFalse(report.is_shared)
            self.assertEqual(ReportComment.query.count(), 0)
            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
