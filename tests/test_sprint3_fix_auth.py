"""Regression tests for patch contract items P1-P4, P8, and P9 (auth, mail, limits)."""

import contextlib
import io
import re
import smtplib
import ssl
import threading
import unittest
from datetime import datetime, timedelta
from unittest import mock

import auth
import mailer
import rate_limit
from extensions import db
from models import User
from rate_limit import AuthAttempt, key_hash
from sprint3_base import Sprint3TestCase
from sprint3_fix_helpers import FakeSMTP, captured_logs

GENERIC = "If an account exists for that email, we sent a reset link."
LIMIT_MESSAGE = "Too many attempts. Try again later."
INVALID_LOGIN = "Invalid email or password."
BASE_URL = "https://pets.example.test"
ADDR_A = "203.0.113.10"
ADDR_B = "203.0.113.20"
WRONG = "WrongPass999!"
LEAK_MARKER = "synthetic-detail-that-must-not-be-logged"
EMAIL_A = "limit-a@example.test"
EMAIL_B = "limit-b@example.test"


class FixTestCase(Sprint3TestCase):
    def use_smtp(self, base_url=BASE_URL, use_tls=False, username=""):
        self.app.config.update(
            MAIL_BACKEND="smtp", APP_BASE_URL=base_url, MAIL_HOST="mail.example.test",
            MAIL_PORT=25, MAIL_FROM="noreply@example.test", MAIL_USE_TLS=use_tls,
            MAIL_USERNAME=username, MAIL_PASSWORD="synthetic-mail-password" if username else "",
        )

    def request_reset(self, email=None, addr=ADDR_A):
        return self.post(self.app.test_client(), "/forgot-password",
                         {"email": email or self.users["owner"]["email"]},
                         follow=True, addr=addr)

    def settle(self, fake):
        self.assertEqual(fake.settle(), [], "mail worker did not finish")

    def attempt_rows(self, scope, email, address):
        with self.app.app_context():
            return AuthAttempt.query.filter_by(
                scope=scope, key_hash=key_hash(email, address)).count()

    def attempt_ids(self, scope, email, address):
        with self.app.app_context():
            rows = AuthAttempt.query.filter_by(scope=scope, key_hash=key_hash(email, address))
            return sorted(row.id for row in rows)


class P1TrustedResetLinkTests(FixTestCase):
    def test_p1_can_build_reset_link_matrix(self):
        cases = (
            (BASE_URL, False, False, "smtp", True),
            (BASE_URL, False, False, "memory", True),
            ("", True, False, "console", True),
            ("", True, False, "memory", True),
            ("", False, True, "console", True),
            ("", False, True, "memory", True),
            ("", True, False, "smtp", False),
            ("", False, True, "smtp", False),
            ("", True, True, "smtp", False),
            ("", False, False, "console", False),
            ("", False, False, "memory", False),
            ("", False, False, "smtp", False),
        )
        for base_url, debug, testing, backend, expected in cases:
            with self.subTest(base_url=base_url, debug=debug, testing=testing, backend=backend):
                self.app.debug = debug
                self.app.testing = testing
                self.app.config.update(APP_BASE_URL=base_url, MAIL_BACKEND=backend)
                with self.app.app_context():
                    self.assertIs(bool(auth._can_build_reset_link()), expected)

    def assert_smtp_without_base_url_sends_nothing(self):
        self.use_smtp(base_url="")
        fake = FakeSMTP()
        with mock.patch("smtplib.SMTP", fake), captured_logs() as logs:
            response = self.request_reset()
            self.settle(fake)
        self.assertEqual(response.status_code, 200)
        self.assertIn(GENERIC, self.page_text(response))
        self.assertFalse(fake.called, "SMTP was used without a trusted APP_BASE_URL")
        self.assertTrue(logs.has_error, "missing APP_BASE_URL was not logged as an error")
        self.assertNotIn("/reset-password/", logs.text)

    def test_p1_smtp_without_base_url_sends_nothing_in_debug(self):
        self.app.testing = False
        self.app.debug = True
        self.assert_smtp_without_base_url_sends_nothing()

    def test_p1_smtp_without_base_url_sends_nothing_in_testing(self):
        self.assert_smtp_without_base_url_sends_nothing()

    def test_p1_smtp_with_base_url_uses_trusted_host(self):
        self.use_smtp()
        fake = FakeSMTP()
        client = self.app.test_client()
        page = client.get("/forgot-password", base_url="http://evil.example.test")
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data).group(1).decode()
        with mock.patch("smtplib.SMTP", fake):
            client.post("/forgot-password", base_url="http://evil.example.test",
                        data={"email": self.users["owner"]["email"], "csrf_token": token})
            self.settle(fake)
        self.assertEqual(len(fake.sent_messages), 1)
        body = fake.sent_messages[0].get_content()
        self.assertIn(f"{BASE_URL}/reset-password/", body)
        self.assertNotIn("evil.example.test", body)


class P2VerifiedTlsTests(FixTestCase):
    def send(self, fake):
        with self.app.app_context(), mock.patch("smtplib.SMTP", fake):
            mailer.send_email("owner@example.test", "Subject", "Body")

    def test_p2_starttls_uses_default_verified_context(self):
        self.use_smtp(use_tls=True)
        fake = FakeSMTP()
        sentinel = ssl.create_default_context()
        with mock.patch("ssl.create_default_context", return_value=sentinel) as factory:
            self.send(fake)
        factory.assert_called_once_with()
        fake.server.starttls.assert_called_once_with(context=sentinel)

    def test_p2_context_verifies_certificate_and_hostname(self):
        self.use_smtp(use_tls=True)
        fake = FakeSMTP()
        self.send(fake)
        context = fake.server.starttls.call_args.kwargs.get("context")
        self.assertIsInstance(context, ssl.SSLContext)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_p2_tls_happens_before_credentials_are_sent(self):
        self.use_smtp(use_tls=True, username="mailer@example.test")
        fake = FakeSMTP()
        self.send(fake)
        names = [call[0] for call in fake.server.method_calls]
        self.assertLess(names.index("starttls"), names.index("login"))
        self.assertLess(names.index("login"), names.index("send_message"))

    def test_p2_mail_use_tls_false_skips_starttls(self):
        self.use_smtp(use_tls=False)
        fake = FakeSMTP()
        self.send(fake)
        fake.server.starttls.assert_not_called()
        fake.server.send_message.assert_called_once()


class P3ReserveAttemptTests(FixTestCase):
    def reserve(self, scope="login", email=EMAIL_A, address=ADDR_A):
        function = getattr(rate_limit, "reserve_attempt", None)
        if function is None:
            self.fail("rate_limit.reserve_attempt is required by patch contract P3")
        return function(scope, email, address)

    def add_rows(self, count, scope="login", email=EMAIL_A, address=ADDR_A, age_seconds=0):
        created = datetime.utcnow() - timedelta(seconds=age_seconds)
        db.session.add_all([
            AuthAttempt(scope=scope, key_hash=key_hash(email, address), created_at=created)
            for _ in range(count)
        ])
        db.session.commit()

    @staticmethod
    def count(scope="login", email=EMAIL_A, address=ADDR_A):
        return AuthAttempt.query.filter_by(
            scope=scope, key_hash=key_hash(email, address)).count()

    def after_insert(self, callback, email=EMAIL_A, address=ADDR_A, scope="login"):
        """Run callback right after the commit that stores a new row for this key.

        This is the exact gap between steps 2 and 3 of reserve_attempt, so a concurrent
        request can be interleaved there without threads or timing.
        """
        real_commit = db.session.commit
        last = {"count": self.count(scope, email, address)}

        def tracked_commit():
            real_commit()
            current = self.count(scope, email, address)
            grew = current > last["count"]
            last["count"] = current
            if grew:
                callback()
                last["count"] = self.count(scope, email, address)

        return mock.patch.object(db.session, "commit", tracked_commit)

    def test_p3_helpers_remain_available(self):
        for name in ("is_limited", "record_attempt", "clear_attempts"):
            self.assertTrue(callable(getattr(rate_limit, name, None)), name)

    def test_p3_allows_exactly_the_limit_for_each_scope(self):
        for scope, setting in (("login", "LOGIN_LIMIT"), ("reset", "RESET_LIMIT")):
            with self.subTest(scope=scope), self.app.app_context():
                limit = self.app.config[setting]
                results = [self.reserve(scope) for _ in range(limit + 2)]
                self.assertEqual(results, [True] * limit + [False, False])
                self.assertEqual(self.count(scope), limit)

    def test_p3_accepted_row_is_committed(self):
        with self.app.app_context():
            self.assertIs(self.reserve(), True)
            db.session.rollback()
            self.assertEqual(self.count(), 1)

    def test_p3_denied_attempt_leaves_no_row_after_rollback(self):
        with self.app.app_context():
            self.add_rows(self.app.config["LOGIN_LIMIT"])
            before = sorted(row.id for row in AuthAttempt.query.all())
            self.assertIs(self.reserve(), False)
            db.session.rollback()
            self.assertEqual(sorted(row.id for row in AuthAttempt.query.all()), before)

    def test_p3_removes_expired_rows_for_this_scope_only(self):
        window = self.app.config["LOGIN_WINDOW_SECONDS"]
        with self.app.app_context():
            self.add_rows(2, age_seconds=window + 5)
            self.add_rows(1, email=EMAIL_B, age_seconds=window + 5)
            self.add_rows(1, scope="reset", age_seconds=window + 5)
            self.assertIs(self.reserve(), True)
            self.assertEqual(self.count(), 1)
            self.assertEqual(self.count(email=EMAIL_B), 0)
            self.assertEqual(self.count(scope="reset"), 1)

    def test_p3_expired_rows_do_not_count_toward_limit(self):
        limit = self.app.config["LOGIN_LIMIT"]
        window = self.app.config["LOGIN_WINDOW_SECONDS"]
        with self.app.app_context():
            self.add_rows(limit, age_seconds=window + 5)
            self.assertIs(self.reserve(), True)

    def test_p3_keys_and_scopes_are_independent(self):
        limit = self.app.config["LOGIN_LIMIT"]
        with self.app.app_context():
            self.add_rows(limit)
            self.assertIs(self.reserve(), False)
            self.assertIs(self.reserve(email=EMAIL_B), True)
            self.assertIs(self.reserve(address=ADDR_B), True)
            self.assertIs(self.reserve(scope="reset"), True)

    def test_p3_rival_inserted_before_count_denies_and_removes_only_own_row(self):
        limit = self.app.config["LOGIN_LIMIT"]
        rival_ids = []

        def rival():
            row = AuthAttempt(scope="login", key_hash=key_hash(EMAIL_A, ADDR_A))
            db.session.add(row)
            real_commit()
            rival_ids.append(row.id)

        with self.app.app_context():
            self.add_rows(limit - 1)
            existing = {row.id for row in AuthAttempt.query.all()}
            real_commit = db.session.commit
            fired = []

            def once():
                if not fired:
                    fired.append(True)
                    rival()

            with self.after_insert(once):
                allowed = self.reserve()
            self.assertIs(allowed, False)
            self.assertEqual(len(rival_ids), 1, "reserve_attempt did not commit its row")
            remaining = {row.id for row in AuthAttempt.query.all()}
            self.assertEqual(remaining, existing | set(rival_ids))

    def test_p3_interleaved_requests_never_exceed_limit(self):
        limit = self.app.config["LOGIN_LIMIT"]
        total = limit + 3
        results = []
        started = []

        def next_request():
            if len(started) >= total - 1:
                return
            started.append(True)
            results.append(self.reserve())

        with self.app.app_context():
            with self.after_insert(next_request):
                results.append(self.reserve())
            self.assertEqual(len(results), total)
            # Fail-closed reservations may admit fewer than the limit, never more.
            self.assertLessEqual(results.count(True), limit)
            self.assertEqual(self.count(), results.count(True))

    def test_p3_last_slot_race_admits_at_most_one_request(self):
        limit = self.app.config["LOGIN_LIMIT"]
        results = []
        started = []

        def rival():
            if not started:
                started.append(True)
                results.append(self.reserve())

        with self.app.app_context():
            self.add_rows(limit - 1)
            with self.after_insert(rival):
                results.append(self.reserve())
            self.assertEqual(len(results), 2)
            self.assertLessEqual(results.count(True), 1)
            self.assertEqual(self.count(), limit - 1 + results.count(True))


class P4LoginAndResetLimitTests(FixTestCase):
    def wrong_login(self, addr=ADDR_A):
        return self.login(self.app.test_client(), password=WRONG, addr=addr)

    def exhaust_reset(self):
        limit = self.app.config["RESET_LIMIT"]
        for _ in range(limit):
            self.request_reset()
        self.assertEqual(len(self.outbox()), limit)
        return limit

    def test_p4_attempt_is_reserved_before_password_check(self):
        email = self.users["owner"]["email"]
        seen = []
        real_check = User.check_password

        def spy(user, password):
            seen.append(AuthAttempt.query.filter_by(
                scope="login", key_hash=key_hash(email, ADDR_A)).count())
            return real_check(user, password)

        with mock.patch.object(User, "check_password", autospec=True, side_effect=spy):
            response = self.wrong_login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen, [1], "no attempt row existed when the password was checked")

    def test_p4_concurrent_login_at_last_slot_checks_one_password(self):
        email = self.users["owner"]["email"]
        limit = self.app.config["LOGIN_LIMIT"]
        for _ in range(limit - 1):
            self.assertEqual(self.wrong_login().status_code, 200)
        rival = self.app.test_client()
        rival_data = {"email": email, "password": WRONG, "csrf_token": self.csrf(rival, ADDR_A)}
        rival_status = []
        calls = []
        real_check = User.check_password

        def spy(user, password):
            calls.append(password)
            if not rival_status:
                rival_status.append(None)
                reply = rival.post("/login", data=rival_data,
                                   environ_overrides={"REMOTE_ADDR": ADDR_A})
                rival_status[0] = reply.status_code
            return real_check(user, password)

        with mock.patch.object(User, "check_password", autospec=True, side_effect=spy):
            response = self.wrong_login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(rival_status, [429])
        self.assertEqual(len(calls), 1, "a concurrent request reached the password check")

    def test_p4_failures_show_normal_error_then_correct_password_gets_429(self):
        for attempt in range(1, self.app.config["LOGIN_LIMIT"] + 1):
            response = self.wrong_login()
            self.assertEqual(response.status_code, 200, f"attempt {attempt}")
            self.assertIn(INVALID_LOGIN, self.page_text(response))
        with mock.patch.object(User, "check_password", autospec=True) as check:
            blocked = self.login(self.app.test_client(), addr=ADDR_A)
        self.assertEqual(blocked.status_code, 429)
        self.assertIn(LIMIT_MESSAGE, self.page_text(blocked))
        check.assert_not_called()

    def test_p4_failed_password_keeps_its_row(self):
        self.wrong_login()
        self.wrong_login()
        self.assertEqual(self.attempt_rows("login", self.users["owner"]["email"], ADDR_A), 2)

    def test_p4_correct_password_clears_only_this_key(self):
        email = self.users["owner"]["email"]
        self.wrong_login(ADDR_A)
        self.wrong_login(ADDR_B)
        self.assertEqual(self.login(self.app.test_client(), addr=ADDR_A).status_code, 302)
        self.assertEqual(self.attempt_rows("login", email, ADDR_A), 0)
        self.assertEqual(self.attempt_rows("login", email, ADDR_B), 1)

    def test_p4_blocked_login_adds_no_row(self):
        email = self.users["owner"]["email"]
        for _ in range(self.app.config["LOGIN_LIMIT"]):
            self.wrong_login()
        before = self.attempt_ids("login", email, ADDR_A)
        self.assertEqual(self.wrong_login().status_code, 429)
        self.assertEqual(self.attempt_ids("login", email, ADDR_A), before)

    def test_p4_blocked_reset_retries_add_no_rows(self):
        email = self.users["owner"]["email"]
        limit = self.exhaust_reset()
        before = self.attempt_ids("reset", email, ADDR_A)
        for _ in range(limit):
            blocked = self.request_reset()
            self.assertEqual(blocked.status_code, 200)
            self.assertIn(GENERIC, self.page_text(blocked))
        self.assertEqual(self.attempt_ids("reset", email, ADDR_A), before)
        self.assertEqual(len(self.outbox()), limit)

    def test_p4_blocked_reset_retries_do_not_extend_block(self):
        email = self.users["owner"]["email"]
        limit = self.exhaust_reset()
        original = self.attempt_ids("reset", email, ADDR_A)
        for _ in range(limit):
            self.request_reset()
        window = self.app.config["RESET_WINDOW_SECONDS"]
        with self.app.app_context():
            AuthAttempt.query.filter(AuthAttempt.id.in_(original)).update(
                {"created_at": datetime.utcnow() - timedelta(seconds=window + 1)},
                synchronize_session=False)
            db.session.commit()
        self.request_reset()
        self.assertEqual(len(self.outbox()), limit + 1)


class P8ResetTimingTests(FixTestCase):
    def background(self):
        function = getattr(mailer, "send_email_background", None)
        if function is None:
            self.fail("mailer.send_email_background is required by patch contract P8")
        return function

    def test_p8_slow_smtp_does_not_delay_reset_response(self):
        self.use_smtp()
        fake = FakeSMTP(hold=True)
        with mock.patch("smtplib.SMTP", fake):
            response = self.request_reset()
            self.assertEqual(response.status_code, 200)
            self.assertIn(GENERIC, self.page_text(response))
            self.assertEqual(fake.server.send_message.call_count, 0,
                             "mail was sent before the response returned")
            self.settle(fake)
        self.assertTrue(fake.called, "reset email was never sent")
        self.assertNotIn(threading.main_thread(), fake.threads)
        self.assertTrue(all(thread.daemon for thread in fake.threads))
        self.assertEqual(len(fake.sent_messages), 1)
        self.assertEqual(fake.sent_messages[0]["To"], self.users["owner"]["email"])

    def test_p8_background_send_has_app_context(self):
        send = self.background()
        self.use_smtp()
        fake = FakeSMTP()
        with mock.patch("smtplib.SMTP", fake), captured_logs() as logs:
            with self.app.app_context():
                send("owner@example.test", "Subject", "Body")
            self.settle(fake)
        self.assertNotIn(threading.main_thread(), fake.threads)
        self.assertEqual(len(fake.sent_messages), 1, logs.text)
        self.assertEqual(fake.sent_messages[0]["From"], "noreply@example.test")

    def test_p8_background_failure_logs_only_error_type(self):
        send = self.background()
        self.use_smtp()
        fake = FakeSMTP(error=smtplib.SMTPException(LEAK_MARKER))
        body = f"{BASE_URL}/reset-password/synthetic-token"
        with mock.patch("smtplib.SMTP", fake), captured_logs() as logs:
            with self.app.app_context():
                send("owner@example.test", "Subject", body)
            self.settle(fake)
        self.assertTrue(fake.called)
        self.assertIn("SMTPException", logs.text)
        self.assertNotIn(LEAK_MARKER, logs.text)
        self.assertNotIn("synthetic-token", logs.text)
        self.assertNotIn("/reset-password/", logs.text)

    def test_p8_reset_flow_failure_stays_generic_and_private(self):
        self.background()
        self.use_smtp()
        fake = FakeSMTP(error=smtplib.SMTPException(LEAK_MARKER))
        with mock.patch("smtplib.SMTP", fake), captured_logs() as logs:
            response = self.request_reset()
            self.settle(fake)
        self.assertEqual(response.status_code, 200)
        self.assertIn(GENERIC, self.page_text(response))
        self.assertNotIn(threading.main_thread(), fake.threads)
        self.assertNotIn(LEAK_MARKER, logs.text)
        self.assertNotIn("/reset-password/", logs.text)

    def test_p8_memory_backend_stays_synchronous(self):
        send = self.background()
        with mock.patch("threading.Thread.start") as start, self.app.app_context():
            send("owner@example.test", "Subject", "Body")
        start.assert_not_called()
        self.assertEqual(len(self.outbox()), 1)

    def test_p8_console_backend_stays_synchronous(self):
        send = self.background()
        self.app.config["MAIL_BACKEND"] = "console"
        output = io.StringIO()
        with mock.patch("threading.Thread.start") as start, self.app.app_context(), \
                contextlib.redirect_stdout(output):
            send("owner@example.test", "Console subject", "Body")
        start.assert_not_called()
        self.assertIn("Console subject", output.getvalue())


class P9RegistrationEmailLengthTests(FixTestCase):
    SUFFIX = "@example.test"

    def register(self, email):
        return self.post(self.app.test_client(), "/register", {
            "email": email, "password": "SyntheticPass123!",
            "confirm_password": "SyntheticPass123!",
        })

    def test_p9_email_over_limit_shows_field_error(self):
        email = "a" * (auth.MAX_EMAIL_LENGTH + 1 - len(self.SUFFIX)) + self.SUFFIX
        self.assertEqual(len(email), auth.MAX_EMAIL_LENGTH + 1)
        response = self.register(email)
        self.assertEqual(response.status_code, 200)
        self.assert_field_error(response, "email")
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(email=email).first())

    def test_p9_email_at_limit_is_accepted(self):
        email = "a" * (auth.MAX_EMAIL_LENGTH - len(self.SUFFIX)) + self.SUFFIX
        self.assertEqual(self.register(email).status_code, 302)
        with self.app.app_context():
            self.assertIsNotNone(User.query.filter_by(email=email).first())


if __name__ == "__main__":
    unittest.main()
