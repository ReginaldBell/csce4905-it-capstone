"""Contract Addenda A (security), B (session_version), and C (handoff clarifications)."""

import contextlib
import hashlib
import io
import logging
import os
import re
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from app import create_app
from extensions import db
from models import Report, ReportPet, User
from sprint3_base import PNG_BYTES, Sprint3Config, Sprint3TestCase

GENERIC = "If an account exists for that email, we sent a reset link."
INVALID = "This reset link is invalid or has expired."
LINK_RE = re.compile(r"(\S*)/reset-password/([A-Za-z0-9_-]+)")
BASE_URL = "https://pets.example.test"
FORGED_HOST = "http://evil.example.test"
ADDR_A = "203.0.113.10"
ADDR_B = "203.0.113.20"
WRONG = "WrongPass999!"
RESOLVED_PHOTO = "Photo unavailable because this report is resolved."


class Records(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append((record.levelno, record.getMessage()))

    @property
    def text(self):
        return "\n".join(message for _level, message in self.records)

    @property
    def has_error(self):
        return any(level >= logging.ERROR for level, _message in self.records)


@contextlib.contextmanager
def captured_logs():
    handler = Records()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield handler
    finally:
        root.removeHandler(handler)


class AddendaBase(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.known = self.users["owner"]
        self.new_password = self.reset_cases["new_password"]

    def request_reset(self, addr=None, client=None):
        return self.post(client or self.app.test_client(), "/forgot-password",
                         {"email": self.known["email"]}, follow=True, addr=addr)

    def issue_token(self, addr=None):
        self.assertEqual(self.request_reset(addr).status_code, 200)
        self.assertTrue(self.outbox(), "no email in mail_outbox")
        match = LINK_RE.search(self.outbox()[-1]["body"])
        self.assertIsNotNone(match, "reset email has no reset link")
        return match.group(2)

    def submit(self, token, addr=None):
        return self.post(self.app.test_client(), f"/reset-password/{token}", {
            "password": self.new_password, "confirm_password": self.new_password}, addr=addr)

    def insert_unused_token(self, raw):
        model = self.model_or_fail("PasswordResetToken")
        now = datetime.utcnow()
        with self.app.app_context():
            db.session.add(model(user_id=self.user_ids["owner"],
                                 token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                                 expires_at=now + timedelta(hours=1), created_at=now))
            db.session.commit()

    def outside_debug(self, base_url=None):
        self.app.testing = False
        self.app.debug = False
        self.app.config["APP_BASE_URL"] = base_url


class AddendumAResetLinkTests(AddendaBase):
    def forged_request(self):
        client = self.app.test_client()
        page = client.get("/forgot-password", base_url=FORGED_HOST)
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data)
        self.assertIsNotNone(token, "no CSRF token on forgot-password page")
        return client.post("/forgot-password", base_url=FORGED_HOST, follow_redirects=True,
                           data={"email": self.known["email"],
                                 "csrf_token": token.group(1).decode()})

    def test_addendum_a_reset_link_uses_app_base_url(self):
        self.app.config["APP_BASE_URL"] = BASE_URL
        self.request_reset()
        self.assertTrue(self.outbox(), "no email in mail_outbox")
        self.assertIn(f"{BASE_URL}/reset-password/", self.outbox()[-1]["body"])

    def test_addendum_a_forged_host_does_not_change_reset_link(self):
        self.app.config["APP_BASE_URL"] = BASE_URL
        self.assertEqual(self.forged_request().status_code, 200)
        self.assertTrue(self.outbox(), "no email in mail_outbox")
        body = self.outbox()[-1]["body"]
        self.assertIn(f"{BASE_URL}/reset-password/", body)
        self.assertNotIn("evil.example.test", body)

    def test_addendum_a_request_host_allowed_when_testing_without_base_url(self):
        self.app.config["APP_BASE_URL"] = None
        self.request_reset()
        self.assertTrue(self.outbox(), "no email in mail_outbox")
        self.assertIn("http://localhost/reset-password/", self.outbox()[-1]["body"])

    def test_addendum_a_no_send_without_base_url_outside_debug(self):
        self.outside_debug()
        env = {k: v for k, v in os.environ.items() if k != "APP_BASE_URL"}
        with mock.patch.dict(os.environ, env, clear=True), captured_logs() as logs:
            response = self.request_reset()
        self.assertEqual(response.status_code, 200)
        self.assertIn(GENERIC, self.page_text(response))
        self.assertEqual(self.outbox(), [])
        self.assertTrue(logs.has_error, "missing APP_BASE_URL was not logged as an error")
        self.assertNotIn("/reset-password/", logs.text)

    def test_addendum_a_sends_with_base_url_outside_debug(self):
        self.outside_debug(BASE_URL)
        self.assertEqual(self.request_reset().status_code, 200)
        self.assertEqual(len(self.outbox()), 1)
        self.assertIn(f"{BASE_URL}/reset-password/", self.outbox()[0]["body"])


class AddendumATokenAndAttemptTests(AddendaBase):
    def test_addendum_a_email_change_invalidates_unused_tokens(self):
        token = self.issue_token()
        self.insert_unused_token("second-unused-email-token")
        self.login(self.owner)
        saved = self.post(self.owner, "/settings", {
            "display_name": "Avery", "full_name": "", "phone": "",
            "email": self.fixtures["users"]["account_update"]["email"],
            "current_password": self.known["password"]})
        self.assertEqual(saved.status_code, 302)
        for raw in (token, "second-unused-email-token"):
            with self.subTest(token=raw):
                response = self.app.test_client().get(f"/reset-password/{raw}")
                self.assertEqual(response.status_code, 400)
                self.assertIn(INVALID, self.page_text(response))

    def test_addendum_a_password_reset_invalidates_all_unused_tokens(self):
        token = self.issue_token()
        self.insert_unused_token("second-unused-reset-token")
        self.assertEqual(self.submit(token).status_code, 302)
        response = self.app.test_client().get("/reset-password/second-unused-reset-token")
        self.assertEqual(response.status_code, 400)
        self.assertIn(INVALID, self.page_text(response))

    def fail_logins(self, addr):
        for _ in range(self.app.config["LOGIN_LIMIT"]):
            self.login(self.app.test_client(), password=WRONG, addr=addr)
        blocked = self.login(self.app.test_client(), password=WRONG, addr=addr)
        self.assertEqual(blocked.status_code, 429)

    def login_new_password(self, addr):
        client = self.app.test_client()
        return self.post(client, "/login", {"email": self.known["email"],
                                            "password": self.new_password}, addr=addr)

    def test_addendum_a_successful_reset_clears_login_attempts(self):
        self.fail_logins(ADDR_A)
        token = self.issue_token(ADDR_A)
        self.assertEqual(self.submit(token, ADDR_A).status_code, 302)
        self.assertEqual(self.login_new_password(ADDR_A).status_code, 302)

    def test_addendum_a_reset_clears_attempts_only_for_current_address(self):
        self.fail_logins(ADDR_A)
        self.fail_logins(ADDR_B)
        token = self.issue_token(ADDR_A)
        self.assertEqual(self.submit(token, ADDR_A).status_code, 302)
        self.assertEqual(self.login_new_password(ADDR_B).status_code, 429)


class AddendumAConsoleMailTests(AddendaBase):
    def test_addendum_a_console_mail_silent_outside_debug(self):
        self.outside_debug(BASE_URL)
        self.app.config["MAIL_BACKEND"] = "console"
        stdout = io.StringIO()
        with captured_logs() as logs, contextlib.redirect_stdout(stdout):
            response = self.request_reset()
        self.assertEqual(response.status_code, 200)
        self.assertIn(GENERIC, self.page_text(response))
        self.assertEqual(stdout.getvalue(), "")
        self.assertTrue(logs.has_error, "console send outside debug was not logged")
        self.assertNotIn("/reset-password/", logs.text)
        self.assertNotIn(self.known["email"], logs.text)

    def test_addendum_a_console_mail_prints_when_testing(self):
        self.app.config.update(MAIL_BACKEND="console", APP_BASE_URL=BASE_URL)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.request_reset()
        self.assertIn(f"{BASE_URL}/reset-password/", stdout.getvalue())


class AddendumASharedPhotoTests(AddendaBase):
    def setUp(self):
        super().setUp()
        self.login_both()
        (self.upload_dir / "shared.png").write_bytes(PNG_BYTES)
        self.pet_id = self.seed_pet(name="Shared Photo Pet", photo_path="uploads/shared.png")
        self.url = "/static/uploads/shared.png"

    def add_report(self, status, shared=True):
        with self.app.app_context():
            report = Report(owner_id=self.user_ids["owner"], status=status, is_shared=shared,
                            last_seen_location="Private synthetic street")
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=self.pet_id))
            db.session.commit()
            return report.id

    def status(self, client):
        response = client.get(self.url)
        code = response.status_code
        response.close()
        return code

    def test_addendum_c_resolved_photo_message_for_non_owner(self):
        for status in ("found", "closed"):
            with self.subTest(status=status):
                report_id = self.add_report(status)
                response = self.other.get(f"/community/reports/{report_id}")
                self.assertEqual(response.status_code, 200)
                text = self.page_text(response)
                self.assertIn(RESOLVED_PHOTO, text)
                self.assertNotIn(self.url, text)

    def test_addendum_c_resolved_photo_stays_visible_to_owner(self):
        report_id = self.add_report("found")
        text = self.page_text(self.owner.get(f"/community/reports/{report_id}"))
        self.assertIn(self.url, text)
        self.assertNotIn(RESOLVED_PHOTO, text)

    def test_addendum_c_open_shared_report_shows_photo_without_message(self):
        report_id = self.add_report("open")
        text = self.page_text(self.other.get(f"/community/reports/{report_id}"))
        self.assertIn(self.url, text)
        self.assertNotIn(RESOLVED_PHOTO, text)

    def test_addendum_a_non_owner_can_open_photo_on_open_shared_report(self):
        self.add_report("open")
        self.assertEqual(self.status(self.other), 200)
        self.assertEqual(self.status(self.owner), 200)

    def test_addendum_a_non_owner_blocked_when_report_found_or_closed(self):
        for status in ("found", "closed"):
            with self.subTest(status=status):
                with self.app.app_context():
                    ReportPet.query.delete()
                    Report.query.delete()
                    db.session.commit()
                self.add_report(status)
                self.assertEqual(self.status(self.other), 404)
                self.assertNotEqual(self.status(self.guest), 200)
                self.assertEqual(self.status(self.owner), 200)

    def test_addendum_a_non_owner_blocked_on_open_unshared_report(self):
        self.add_report("open", shared=False)
        self.assertEqual(self.status(self.other), 404)
        self.assertEqual(self.status(self.owner), 200)

    def test_addendum_a_any_open_shared_report_allows_non_owner(self):
        self.add_report("closed")
        self.add_report("open")
        self.assertEqual(self.status(self.other), 200)


class AddendumBSessionVersionTests(AddendaBase):
    def set_session(self, client, value):
        with client.session_transaction() as session:
            session["_user_id"] = value
            session["_fresh"] = True

    def set_version(self, version):
        with self.app.app_context():
            db.session.get(User, self.user_ids["owner"]).session_version = version
            db.session.commit()

    def test_addendum_b_get_id_includes_session_version(self):
        with self.app.app_context():
            user = db.session.get(User, self.user_ids["owner"])
            self.assertEqual(getattr(user, "session_version", None), 1)
            self.assertEqual(user.get_id(), f"{user.id}:1")

    def test_addendum_b_session_before_reset_is_logged_out(self):
        self.assertEqual(self.login(self.owner).status_code, 302)
        self.assertEqual(self.owner.get("/settings").status_code, 200)
        token = self.issue_token()
        self.assertEqual(self.submit(token).status_code, 302)
        self.assertEqual(self.user_value("owner", "session_version"), 2)
        self.assert_redirects_to_login(self.owner.get("/settings"))

    def test_addendum_b_session_after_reset_works(self):
        token = self.issue_token()
        self.assertEqual(self.submit(token).status_code, 302)
        client = self.app.test_client()
        login = self.post(client, "/login", {"email": self.known["email"],
                                             "password": self.new_password})
        self.assertEqual(login.status_code, 302)
        self.assertEqual(client.get("/settings").status_code, 200)

    def test_addendum_b_legacy_plain_id_counts_as_version_1(self):
        self.set_session(self.owner, str(self.user_ids["owner"]))
        self.assertEqual(self.user_value("owner", "session_version"), 1)
        self.assertEqual(self.owner.get("/settings").status_code, 200)

    def test_addendum_b_legacy_plain_id_rejected_after_version_change(self):
        self.assertEqual(self.user_value("owner", "session_version"), 1)
        self.set_version(2)
        self.set_session(self.owner, str(self.user_ids["owner"]))
        self.assert_redirects_to_login(self.owner.get("/settings"))

    def test_addendum_b_version_mismatch_is_rejected(self):
        self.assertEqual(self.user_value("owner", "session_version"), 1)
        self.set_session(self.owner, f"{self.user_ids['owner']}:99")
        self.assert_redirects_to_login(self.owner.get("/settings"))

    def test_addendum_b_matching_version_is_accepted(self):
        self.set_version(3)
        self.set_session(self.owner, f"{self.user_ids['owner']}:3")
        self.assertEqual(self.owner.get("/settings").status_code, 200)


class AddendumBUpgradeTests(unittest.TestCase):
    LEGACY_SCHEMA = """
        CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL, display_name VARCHAR(50),
            created_at DATETIME NOT NULL);
        CREATE TABLE pets (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL, species VARCHAR(50) NOT NULL, breed VARCHAR(100),
            birth_date DATE, notes TEXT, photo_path VARCHAR(255), photo_uploaded_at DATETIME,
            created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
        CREATE TABLE contacts (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL,
            category VARCHAR(50) NOT NULL, name VARCHAR(100) NOT NULL, phone VARCHAR(30),
            email VARCHAR(255), notes TEXT, created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL);
        INSERT INTO users VALUES (1, 'legacy@example.test', 'hash', 'Legacy',
            '2026-01-01 00:00:00');
        INSERT INTO pets (id, owner_id, name, species, created_at, updated_at)
            VALUES (1, 1, 'Legacy Pet', 'Dog', '2026-01-01 00:00:00', '2026-01-01 00:00:00');
        INSERT INTO contacts (id, owner_id, category, name, phone, created_at, updated_at)
            VALUES (1, 1, 'Other', 'Legacy Contact', '555-0120', '2026-01-01 00:00:00',
            '2026-01-01 00:00:00');
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "legacy.db"
        connection = sqlite3.connect(self.path)
        connection.executescript(self.LEGACY_SCHEMA)
        connection.commit()
        connection.close()

        class UpgradeConfig(Sprint3Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.path}"
            UPLOAD_FOLDER = str(Path(self.tmp.name) / "uploads")

        self.app = create_app(UpgradeConfig)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tmp.cleanup()

    def query(self, sql):
        connection = sqlite3.connect(self.path)
        try:
            return connection.execute(sql).fetchall()
        finally:
            connection.close()

    def invoke(self, command):
        result = self.app.test_cli_runner().invoke(args=[command])
        self.assertEqual(result.exit_code, 0, f"{command}: {result.output}")

    def columns(self, table):
        return {row[1] for row in self.query(f"PRAGMA table_info({table})")}

    def test_addendum_b_upgrade_adds_session_version_and_keeps_records(self):
        # Documented order, with each command run twice to prove it is repeatable.
        for command in ("upgrade-community", "upgrade-community",
                        "upgrade-sprint3", "upgrade-sprint3"):
            self.invoke(command)
        self.assertLessEqual({"session_version", "full_name", "phone"}, self.columns("users"))
        self.assertLessEqual({"sex", "height_inches", "weight_lbs", "colors", "markings",
                              "microchip_status", "microchip_number"}, self.columns("pets"))
        self.assertIn("address", self.columns("contacts"))
        self.assertEqual(self.query("SELECT email, session_version FROM users"),
                         [("legacy@example.test", 1)])
        self.assertEqual(self.query("SELECT name FROM pets"), [("Legacy Pet",)])
        self.assertEqual(self.query("SELECT name FROM contacts"), [("Legacy Contact",)])
        tables = {row[0] for row in self.query("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertLessEqual({"password_reset_tokens", "auth_attempts"}, tables)

    def test_addendum_c_upgrade_community_adds_user_columns_only(self):
        self.invoke("upgrade-community")
        self.assertLessEqual({"session_version", "full_name", "phone"}, self.columns("users"))
        self.assertEqual(self.query("SELECT session_version FROM users"), [(1,)])
        with self.app.app_context():
            self.assertEqual(User.query.one().email, "legacy@example.test")
        self.assertNotIn("sex", self.columns("pets"))
        self.assertNotIn("microchip_number", self.columns("pets"))
        self.assertNotIn("address", self.columns("contacts"))


if __name__ == "__main__":
    unittest.main()
