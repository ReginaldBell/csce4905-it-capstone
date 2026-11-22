"""TC-004: account name, phone, and email; saved phone appears in generated outputs."""

import unittest

from extensions import db
from models import Report, ReportPet, User
from sprint3_base import MISSING, Sprint3TestCase
from sprint3_data import expand_value


class AccountDetailsTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.login_both()
        self.update = self.fixtures["users"]["account_update"]
        self.owner_row = self.users["owner"]

    def values(self, **changes):
        values = {
            "display_name": self.update["display_name"],
            "full_name": self.update["full_name"],
            "phone": self.update["phone"],
            "email": self.owner_row["email"],
            "current_password": "",
        }
        values.update(changes)
        return values

    def save(self, **changes):
        return self.post(self.owner, "/settings", self.values(**changes))

    def seed_report(self):
        pet_id = self.seed_pet(name="Output Pet")
        with self.app.app_context():
            report = Report(owner_id=self.user_ids["owner"], status="open",
                            last_seen_location="Synthetic Park")
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=pet_id))
            db.session.commit()
            return report.id

    def test_tc_004_name_and_phone_persist_after_reopening_settings(self):
        self.assertEqual(self.save().status_code, 302)
        self.assertEqual(self.user_value("owner", "display_name"), self.update["display_name"])
        self.assertEqual(self.user_value("owner", "full_name"), self.update["full_name"])
        self.assertEqual(self.user_value("owner", "phone"), self.update["phone"])
        page = self.owner.get("/settings")
        for field in ("display_name", "full_name", "phone"):
            self.assertEqual(self.control_value(page, field), self.update[field])
        self.assertEqual(self.control_value(page, "email"), self.owner_row["email"])

    def test_tc_004_email_change_with_correct_password_normalizes_and_logs_in(self):
        response = self.save(email=f"  {self.update['email'].upper()} ",
                             current_password=self.owner_row["password"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user_value("owner", "email"), self.update["email"])
        self.logout(self.owner)
        client = self.app.test_client()
        rejected = self.post(client, "/login", {"email": self.owner_row["email"],
                                                "password": self.owner_row["password"]})
        self.assertEqual(rejected.status_code, 200)
        accepted = self.post(client, "/login", {"email": self.update["email"],
                                                "password": self.owner_row["password"]})
        self.assertEqual(accepted.status_code, 302)

    def test_tc_004_email_change_requires_correct_current_password(self):
        for password in ("", "WrongPass999!"):
            with self.subTest(password=password):
                response = self.save(email=self.update["email"], current_password=password)
                self.assertEqual(response.status_code, 200)
                self.assert_field_error(response, "current_password")
                self.assertEqual(self.user_value("owner", "email"), self.owner_row["email"])

    def test_tc_004_invalid_email_is_rejected(self):
        response = self.save(email="not-an-email", current_password=self.owner_row["password"])
        self.assertEqual(response.status_code, 200)
        self.assert_field_error(response, "email")
        self.assertEqual(self.user_value("owner", "email"), self.owner_row["email"])

    def test_tc_004_duplicate_email_is_rejected(self):
        response = self.save(email=self.users["other"]["email"].upper(),
                             current_password=self.owner_row["password"])
        self.assertEqual(response.status_code, 200)
        self.assert_field_error(response, "email")
        self.assertEqual(self.user_value("owner", "email"), self.owner_row["email"])

    def test_tc_004_invalid_values_are_rejected_and_preserved(self):
        for case in self.invalid["account"]:
            with self.subTest(case=case["id"]):
                value = expand_value(case["value"])
                extra = {"current_password": self.owner_row["password"]}
                response = self.save(**{case["field"]: value}, **extra)
                self.assertEqual(response.status_code, 200)
                self.assert_field_error(response, case["field"])
                self.assertEqual(self.control_value(response, case["field"]), value)
                self.assertEqual(self.user_value("owner", "email"), self.owner_row["email"])
                self.assertIn(self.user_value("owner", "phone"), (None, MISSING))

    def test_tc_004_generated_outputs_use_saved_phone_and_email(self):
        report_id = self.seed_report()
        contact_id = self.seed_contact("vet_full")
        self.assertEqual(self.save().status_code, 302)
        for route in (f"/reports/{report_id}/email/{contact_id}",
                      f"/reports/{report_id}/phone-script/{contact_id}",
                      f"/reports/{report_id}/social-post",
                      f"/reports/{report_id}/flyer"):
            with self.subTest(route=route):
                response = self.owner.get(route)
                self.assertEqual(response.status_code, 200)
                text = self.page_text(response)
                self.assertIn(self.update["phone"], text)
                self.assertIn(self.owner_row["email"], text)

    def test_tc_004_settings_changes_do_not_affect_other_account(self):
        self.assertEqual(self.save().status_code, 302)
        self.assertEqual(self.user_value("other", "display_name"),
                         self.users["other"]["display_name"])
        self.assertIn(self.user_value("other", "phone"), (None, MISSING))


if __name__ == "__main__":
    unittest.main()
