"""TC-609 and TC-1014: sign-in and reset limits defined by the Sprint 3 contract.

Report and tip limits named in the tracker are not defined by the contract, and tips do
not exist until Sprint 5. They are recorded as not covered in SPRINT3_CASE_MAP.md.
"""

import re
import unittest
from unittest import mock

from extensions import db
from models import User
from sprint3_base import Sprint3TestCase

LIMIT_MESSAGE = "Too many attempts. Try again later."
GENERIC = "If an account exists for that email, we sent a reset link."
ADDR_A = "203.0.113.10"
ADDR_B = "203.0.113.20"
WRONG = "WrongPass999!"


class RequestLimitTests(Sprint3TestCase):
    def fail_login(self, key="owner", addr=ADDR_A, client=None):
        return self.login(client or self.app.test_client(), key, password=WRONG, addr=addr)

    def exhaust_login(self, key="owner", addr=ADDR_A):
        for attempt in range(self.app.config["LOGIN_LIMIT"]):
            response = self.fail_login(key, addr)
            self.assertEqual(response.status_code, 200, f"attempt {attempt + 1}")
            self.assertIn("Invalid email or password.", self.page_text(response))

    def reset(self, email=None, addr=ADDR_A, headers=None):
        return self.post(self.app.test_client(), "/forgot-password",
                         {"email": email or self.users["owner"]["email"]},
                         follow=True, addr=addr, headers=headers)

    def test_tc_609_normal_login_and_reset_work(self):
        response = self.login(self.app.test_client(), addr=ADDR_A)
        self.assertEqual(response.status_code, 302)
        response = self.reset()
        self.assertEqual(response.status_code, 200)
        self.assertIn(GENERIC, self.page_text(response))
        self.assertEqual(len(self.outbox()), 1)

    def test_tc_609_login_over_limit_returns_429(self):
        self.exhaust_login()
        response = self.fail_login()
        self.assertEqual(response.status_code, 429)
        self.assertIn(LIMIT_MESSAGE, self.page_text(response))

    def test_tc_609_correct_password_is_blocked_over_limit(self):
        self.exhaust_login()
        client = self.app.test_client()
        response = self.login(client, addr=ADDR_A)
        self.assertEqual(response.status_code, 429)
        self.assert_redirects_to_login(client.get("/pets", environ_overrides={
            "REMOTE_ADDR": ADDR_A}))

    def test_tc_609_password_is_not_checked_over_limit(self):
        self.exhaust_login()
        with mock.patch.object(User, "check_password", autospec=True) as check:
            response = self.login(self.app.test_client(), addr=ADDR_A)
        self.assertEqual(response.status_code, 429)
        check.assert_not_called()

    def test_tc_609_reset_over_limit_is_generic_and_sends_nothing(self):
        limit = self.app.config["RESET_LIMIT"]
        pages = [self.reset() for _ in range(limit)]
        self.assertEqual(len(self.outbox()), limit)
        blocked = self.reset()
        self.assertEqual(blocked.status_code, 200)
        self.assertIn(GENERIC, self.page_text(blocked))
        self.assertNotIn(LIMIT_MESSAGE, self.page_text(blocked))
        self.assertEqual(len(self.outbox()), limit)
        strip = lambda r: re.sub(r'name="csrf_token"[^>]*value="[^"]+"', "",
                                 r.get_data(as_text=True))
        self.assertEqual(strip(blocked), strip(pages[0]))

    def test_tc_1014_login_boundary_is_exactly_at_limit(self):
        for attempt in range(1, self.app.config["LOGIN_LIMIT"] + 1):
            self.assertEqual(self.fail_login().status_code, 200, f"attempt {attempt}")
        self.assertEqual(self.fail_login().status_code, 429)

    def test_tc_1014_successful_login_clears_failed_attempts(self):
        for _ in range(self.app.config["LOGIN_LIMIT"] - 1):
            self.fail_login()
        self.assertEqual(self.login(self.app.test_client(), addr=ADDR_A).status_code, 302)
        self.exhaust_login()
        self.assertEqual(self.fail_login().status_code, 429)

    def test_tc_1014_successful_login_does_not_count(self):
        for _ in range(self.app.config["LOGIN_LIMIT"] + 2):
            self.assertEqual(self.login(self.app.test_client(), addr=ADDR_A).status_code, 302)

    def test_tc_1014_login_limit_is_per_email(self):
        self.exhaust_login("owner")
        self.assertEqual(self.fail_login("owner").status_code, 429)
        self.assertEqual(self.login(self.app.test_client(), "other", addr=ADDR_A).status_code, 302)

    def test_tc_1014_login_limit_is_per_client_address(self):
        self.exhaust_login("owner", ADDR_A)
        self.assertEqual(self.fail_login("owner", ADDR_A).status_code, 429)
        self.assertEqual(self.login(self.app.test_client(), "owner", addr=ADDR_B).status_code, 302)

    def test_tc_1014_login_ignores_forwarded_headers(self):
        self.exhaust_login()
        client = self.app.test_client()
        data = {"email": self.users["owner"]["email"], "password": WRONG,
                "csrf_token": self.csrf(client, ADDR_A)}
        response = client.post("/login", data=data, headers={"X-Forwarded-For": ADDR_B},
                               environ_overrides={"REMOTE_ADDR": ADDR_A})
        self.assertEqual(response.status_code, 429)

    def test_tc_1014_reset_boundary_is_exactly_at_limit(self):
        limit = self.app.config["RESET_LIMIT"]
        for attempt in range(1, limit + 1):
            self.reset()
            self.assertEqual(len(self.outbox()), attempt)
        self.reset()
        self.assertEqual(len(self.outbox()), limit)

    def test_tc_1014_reset_limit_is_per_email(self):
        limit = self.app.config["RESET_LIMIT"]
        for _ in range(limit + 1):
            self.reset()
        self.assertEqual(len(self.outbox()), limit)
        self.reset(self.users["other"]["email"])
        self.assertEqual(len(self.outbox()), limit + 1)
        self.assertEqual(self.outbox()[-1]["to"], self.users["other"]["email"])

    def test_tc_1014_reset_limit_is_per_client_address(self):
        limit = self.app.config["RESET_LIMIT"]
        for _ in range(limit + 1):
            self.reset(addr=ADDR_A)
        self.assertEqual(len(self.outbox()), limit)
        self.reset(addr=ADDR_B)
        self.assertEqual(len(self.outbox()), limit + 1)

    def test_tc_1014_reset_ignores_forwarded_headers(self):
        limit = self.app.config["RESET_LIMIT"]
        for _ in range(limit):
            self.reset()
        self.reset(headers={"X-Forwarded-For": ADDR_B})
        self.assertEqual(len(self.outbox()), limit)

    def test_tc_1014_attempts_store_only_hashed_keys(self):
        model = self.model_or_fail("AuthAttempt")
        self.fail_login()
        self.reset()
        email = self.users["owner"]["email"]
        with self.app.app_context():
            rows = model.query.all()
            self.assertEqual({row.scope for row in rows}, {"login", "reset"})
            for row in rows:
                self.assertRegex(row.key_hash, r"^[0-9a-f]{64}$")
                self.assertNotIn(email, row.key_hash)
                self.assertNotIn(ADDR_A, row.key_hash)

    def test_tc_1014_expired_attempts_no_longer_count(self):
        model = self.model_or_fail("AuthAttempt")
        from datetime import datetime, timedelta
        self.exhaust_login()
        self.assertEqual(self.fail_login().status_code, 429)
        window = self.app.config["LOGIN_WINDOW_SECONDS"]
        with self.app.app_context():
            model.query.update({"created_at": datetime.utcnow() - timedelta(seconds=window + 1)})
            db.session.commit()
        self.assertEqual(self.login(self.app.test_client(), addr=ADDR_A).status_code, 302)


if __name__ == "__main__":
    unittest.main()
