"""TC-005: password reset, including token storage, expiry, reuse, and mail failure."""

import hashlib
import logging
import os
import re
import unittest
from datetime import datetime, timedelta
from unittest import mock

from extensions import db
from models import User
from sprint3_base import Sprint3TestCase

GENERIC = "If an account exists for that email, we sent a reset link."
INVALID = "This reset link is invalid or has expired."
LINK_RE = re.compile(r"/reset-password/([A-Za-z0-9_-]+)")


class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        text = record.getMessage()
        if record.exc_info:
            text += logging.Formatter().formatException(record.exc_info)
        self.lines.append(text)


class PasswordResetTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.known = self.users[self.reset_cases["known_user"]]
        self.new_password = self.reset_cases["new_password"]

    def request_reset(self, email=None, client=None):
        return self.post(client or self.app.test_client(), "/forgot-password",
                         {"email": email or self.known["email"]}, follow=True)

    def issue_token(self):
        self.assertEqual(self.request_reset().status_code, 200)
        outbox = self.outbox()
        self.assertTrue(outbox, "no email in mail_outbox")
        match = LINK_RE.search(outbox[-1]["body"])
        self.assertIsNotNone(match, "reset email has no reset link")
        return match.group(1)

    def submit(self, token, password=None, confirm=None, client=None):
        password = self.new_password if password is None else password
        return self.post(client or self.app.test_client(), f"/reset-password/{token}", {
            "password": password,
            "confirm_password": password if confirm is None else confirm,
        })

    def token_row(self, token):
        model = self.model_or_fail("PasswordResetToken")
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = model.query.filter_by(token_hash=digest).first()
        self.assertIsNotNone(row, "token is not stored as a SHA-256 hash")
        return row

    def password_works(self, password):
        with self.app.app_context():
            return db.session.get(User, self.user_ids["owner"]).check_password(password)

    @staticmethod
    def normalized(response, email):
        text = response.get_data(as_text=True).replace(email, "EMAIL")
        return re.sub(r'(name="csrf_token"[^>]*value=|name="csrf-token"[^>]*content=)"[^"]+"',
                      r'\1"TOKEN"', text)

    def test_tc_005_login_page_links_to_forgot_password(self):
        self.assertIn('href="/forgot-password"', self.guest.get("/login").get_data(as_text=True))

    def test_tc_005_forgot_password_page_has_email_field(self):
        response = self.guest.get("/forgot-password")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="email"', response.data)

    def test_tc_005_known_and_unknown_email_get_identical_response(self):
        known = self.request_reset(self.known["email"])
        unknown = self.request_reset(self.reset_cases["unknown_email"])
        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertIn(GENERIC, self.page_text(known))
        self.assertEqual(self.normalized(known, self.known["email"]),
                         self.normalized(unknown, self.reset_cases["unknown_email"]))

    def test_tc_005_only_known_email_receives_message(self):
        self.request_reset(self.reset_cases["unknown_email"])
        self.assertEqual(self.outbox(), [])
        self.request_reset(self.known["email"])
        outbox = self.outbox()
        self.assertEqual(len(outbox), 1)
        self.assertEqual(set(outbox[0]), {"to", "subject", "body"})
        self.assertEqual(outbox[0]["to"], self.known["email"])
        self.assertRegex(outbox[0]["body"], LINK_RE)

    def test_tc_005_token_is_stored_only_as_hash_with_default_ttl(self):
        started = datetime.utcnow()
        token = self.issue_token()
        with self.app.app_context():
            row = self.token_row(token)
            self.assertEqual(len(row.token_hash), 64)
            self.assertNotEqual(row.token_hash, token)
            self.assertEqual(row.user_id, self.user_ids["owner"])
            self.assertIsNone(row.used_at)
            self.assertGreaterEqual(row.expires_at, started + timedelta(minutes=59))
            self.assertLessEqual(row.expires_at, datetime.utcnow() + timedelta(minutes=61))

    def test_tc_005_valid_link_resets_password_once(self):
        token = self.issue_token()
        self.assertEqual(self.app.test_client().get(f"/reset-password/{token}").status_code, 200)
        response = self.submit(token)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertTrue(self.password_works(self.new_password))
        self.assertFalse(self.password_works(self.known["password"]))
        with self.app.app_context():
            self.assertIsNotNone(self.token_row(token).used_at)

    def test_tc_005_reused_link_is_rejected(self):
        token = self.issue_token()
        self.assertEqual(self.submit(token).status_code, 302)
        for response in (self.app.test_client().get(f"/reset-password/{token}"),
                         self.submit(token, "SyntheticReset299!")):
            self.assertEqual(response.status_code, 400)
            self.assertIn(INVALID, self.page_text(response))
        self.assertTrue(self.password_works(self.new_password))

    def test_tc_005_expired_link_is_rejected(self):
        token = self.issue_token()
        with self.app.app_context():
            self.token_row(token).expires_at = datetime.utcnow() - timedelta(minutes=1)
            db.session.commit()
        for response in (self.app.test_client().get(f"/reset-password/{token}"),
                         self.submit(token)):
            self.assertEqual(response.status_code, 400)
            self.assertIn(INVALID, self.page_text(response))
        self.assertTrue(self.password_works(self.known["password"]))

    def test_tc_005_invalid_link_is_rejected(self):
        for token in self.reset_cases["invalid_tokens"]:
            with self.subTest(token=token):
                for response in (self.app.test_client().get(f"/reset-password/{token}"),
                                 self.submit(token)):
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(INVALID, self.page_text(response))
        self.assertTrue(self.password_works(self.known["password"]))

    def test_tc_005_new_request_invalidates_earlier_token(self):
        first = self.issue_token()
        second = self.issue_token()
        self.assertNotEqual(first, second)
        self.assertEqual(self.submit(first).status_code, 400)
        self.assertTrue(self.password_works(self.known["password"]))
        self.assertEqual(self.submit(second).status_code, 302)

    def test_tc_005_password_rules_match_registration_and_keep_token(self):
        token = self.issue_token()
        for case in self.reset_cases["invalid_passwords"]:
            with self.subTest(case=case["id"]):
                response = self.submit(token, case["password"], case["confirm_password"])
                self.assertEqual(response.status_code, 200)
                self.assert_field_error(response, case["error_field"])
                self.assertTrue(self.password_works(self.known["password"]))
                with self.app.app_context():
                    self.assertIsNone(self.token_row(token).used_at)
        self.assertEqual(self.submit(token).status_code, 302)

    def test_tc_005_logs_never_contain_password_or_hash(self):
        capture = LogCapture()
        root = logging.getLogger()
        root.addHandler(capture)
        previous = root.level
        root.setLevel(logging.DEBUG)
        try:
            token = self.issue_token()
            self.assertEqual(self.submit(token).status_code, 302)
        finally:
            root.removeHandler(capture)
            root.setLevel(previous)
        with self.app.app_context():
            stored = db.session.get(User, self.user_ids["owner"]).password_hash
        logged = "\n".join(capture.lines)
        self.assertNotIn(self.new_password, logged)
        self.assertNotIn(stored, logged)

    def test_tc_005_send_failure_is_logged_without_token_and_stays_generic(self):
        self.app.config.update(MAIL_BACKEND="smtp", MAIL_HOST="mail.example.test", MAIL_PORT=25,
                               MAIL_FROM="noreply@example.test", MAIL_USE_TLS=False)
        capture = LogCapture()
        root = logging.getLogger()
        root.addHandler(capture)
        env = {"MAIL_HOST": "mail.example.test", "MAIL_PORT": "25",
               "MAIL_FROM": "noreply@example.test", "MAIL_USE_TLS": "false"}
        try:
            with mock.patch.dict(os.environ, env), \
                    mock.patch("smtplib.SMTP", side_effect=OSError("synthetic failure")), \
                    mock.patch("smtplib.SMTP_SSL", side_effect=OSError("synthetic failure")):
                response = self.request_reset()
        finally:
            root.removeHandler(capture)
        self.assertEqual(response.status_code, 200)
        self.assertIn(GENERIC, self.page_text(response))
        self.assertTrue(capture.lines, "send failure was not logged")
        logged = "\n".join(capture.lines)
        self.assertNotIn("/reset-password/", logged)
        model = self.model_or_fail("PasswordResetToken")
        with self.app.app_context():
            for row in model.query.all():
                self.assertNotIn(row.token_hash, logged)


if __name__ == "__main__":
    unittest.main()
