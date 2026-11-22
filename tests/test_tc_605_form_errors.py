"""TC-605: form errors identify the field, keep entries, and save no invalid data."""

import re
import unittest

from extensions import db
from models import Pet, Report, ReportPet
from sprint3_base import Sprint3TestCase, parse_page
from sprint3_data import expand_value


class FormErrorTests(Sprint3TestCase):
    def report_count(self):
        with self.app.app_context():
            return Report.query.count()

    def test_tc_605_register_errors_are_tied_to_controls(self):
        response = self.post(self.guest, "/register", {
            "email": "bad-email", "password": "short", "confirm_password": "different"})
        self.assertEqual(response.status_code, 200)
        self.assert_field_error(response, "email")
        self.assert_field_error(response, "password")
        self.assertEqual(self.control_value(response, "email"), "bad-email")

    def test_tc_605_login_error_is_shown_and_email_kept(self):
        response = self.login(self.guest, "owner", password="WrongPass999!")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid email or password.", self.page_text(response))
        self.assertEqual(self.control_value(response, "email"), self.users["owner"]["email"])

    def test_tc_605_pet_required_errors_are_tied_to_controls(self):
        self.login(self.owner)
        response = self.post(self.owner, "/pets/new", {"name": "", "species": "",
                                                       "breed": "Kept Breed"})
        self.assertEqual(response.status_code, 200)
        self.assert_field_error(response, "name")
        self.assert_field_error(response, "species")
        self.assertEqual(self.control_value(response, "breed"), "Kept Breed")

    def test_tc_605_each_invalid_pet_field_is_identified_and_not_saved(self):
        self.login(self.owner)
        before = self.pet_count()
        for case in self.invalid["pet"]:
            with self.subTest(case=case["id"]):
                value = expand_value(case["value"])
                changes = {case["field"]: value, **case.get("extra", {})}
                values = self.pet_values("full_profile", **changes)
                response = self.post(self.owner, "/pets/new", values)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.pet_count(), before)
                self.assert_field_error(response, case["field"])
                self.assertEqual(self.control_value(response, "name"), values["name"])
                self.assertEqual(self.control_value(response, "markings"), values["markings"]
                                 if case["field"] != "markings" else value)
                if parse_page(response).named(case["field"])[0]["tag"] != "select":
                    self.assertEqual(self.control_value(response, case["field"]), value.strip())

    def test_tc_605_invalid_pet_edit_keeps_saved_record(self):
        self.login(self.owner)
        pet_id = self.seed_pet(name="Stable Pet")
        for case in self.invalid["pet"]:
            with self.subTest(case=case["id"]):
                changes = {case["field"]: expand_value(case["value"]), **case.get("extra", {})}
                values = self.pet_values("full_profile", name="Changed Name", **changes)
                response = self.post(self.owner, f"/pets/{pet_id}/edit", values)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.pet_snapshot(pet_id)["name"], "Stable Pet")

    def test_tc_605_boundary_pet_values_are_accepted(self):
        self.login(self.owner)
        for changes in (
            {"height_inches": "120", "weight_lbs": "500"},
            {"height_inches": "0.1", "weight_lbs": "0.1"},
            {"colors": "c" * 100, "markings": "m" * 255},
            {"microchip_status": "chipped", "microchip_number": "A" * 9},
            {"microchip_status": "chipped", "microchip_number": "A1" * 7 + "B"},
        ):
            with self.subTest(changes=sorted(changes)):
                response = self.post(self.owner, "/pets/new",
                                     self.pet_values("full_profile", **changes))
                self.assertEqual(response.status_code, 302)

    def test_tc_605_contact_errors_are_tied_to_controls_and_keep_entries(self):
        self.login(self.owner)
        before = self.contact_count()
        for case in self.invalid["contact"]:
            with self.subTest(case=case["id"]):
                value = expand_value(case["value"])
                values = self.contact_values("vet_full", **{case["field"]: value})
                response = self.post(self.owner, "/contacts/new", values)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.contact_count(), before)
                self.assert_field_error(response, case["field"])
                self.assertEqual(self.control_value(response, case["field"]), value)
                kept = "notes" if case["field"] != "notes" else "category"
                self.assertEqual(self.control_value(response, kept), values[kept])

    def test_tc_605_report_error_keeps_entries_then_correction_saves(self):
        self.login(self.owner)
        first = self.seed_pet(name="Selected Pet")
        second = self.seed_pet(name="Unselected Pet")
        values = {"last_seen_location": "", "last_seen_at": "2026-01-02T03:04",
                  "tz_offset_minutes": "0", "notes": "Kept report note", "pet_ids": [str(first)]}
        response = self.post(self.owner, "/reports/new", values)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.report_count(), 0)
        self.assert_field_error(response, "last_seen_location")
        self.assertEqual(self.control_value(response, "notes"), "Kept report note")
        self.assertEqual(self.control_value(response, "last_seen_at"), "2026-01-02T03:04")
        checked = {c["attrs"]["value"] for c in parse_page(response).named("pet_ids")
                   if "checked" in c["attrs"]}
        self.assertEqual(checked, {str(first)})
        self.assertNotIn(str(second), checked)
        corrected = self.post(self.owner, "/reports/new",
                              {**values, "last_seen_location": "Synthetic Park"})
        self.assertEqual(corrected.status_code, 302)
        with self.app.app_context():
            report = Report.query.one()
            self.assertEqual(report.notes, "Kept report note")
            self.assertEqual([link.pet_id for link in report.report_pets], [first])

    def test_tc_605_report_without_pet_identifies_pet_field(self):
        self.login(self.owner)
        self.seed_pet()
        response = self.post(self.owner, "/reports/new", {"last_seen_location": "Synthetic Park",
                                                          "notes": "Kept report note"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.report_count(), 0)
        self.assert_field_error(response, "pet_ids")
        self.assertEqual(self.control_value(response, "last_seen_location"), "Synthetic Park")

    def test_tc_605_every_form_control_has_a_label(self):
        self.login(self.owner)
        pet_id = self.seed_pet()
        contact_id = self.seed_contact("vet_full")
        routes = ("/pets/new", f"/pets/{pet_id}/edit", "/contacts/new",
                  f"/contacts/{contact_id}/edit", "/reports/new", "/settings")
        for route in routes:
            with self.subTest(route=route):
                response = self.owner.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(parse_page(response).unlabeled(), [])
        for route in ("/login", "/register", "/forgot-password"):
            with self.subTest(route=route):
                response = self.guest.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(parse_page(response).unlabeled(), [])


if __name__ == "__main__":
    unittest.main()
