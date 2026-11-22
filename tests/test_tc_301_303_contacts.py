"""TC-301 to TC-303: contacts with addresses, validation, and privacy."""

import unittest

from extensions import db
from models import Contact
from sprint3_base import MISSING, Sprint3TestCase
from sprint3_data import expand_value


class ContactTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.login_both()

    def create(self, key, **changes):
        response = self.post(self.owner, "/contacts/new", self.contact_values(key, **changes))
        self.assertEqual(response.status_code, 302, "contact was not saved")
        return int(response.headers["Location"].rstrip("/").rsplit("/", 1)[-1])

    def stored(self, contact_id, field):
        with self.app.app_context():
            return getattr(db.session.get(Contact, contact_id), field, MISSING)

    def snapshot(self, contact_id):
        with self.app.app_context():
            contact = db.session.get(Contact, contact_id)
            return None if contact is None else (
                contact.owner_id, contact.category, contact.name, contact.phone, contact.email)

    def test_tc_301_phone_only_and_email_only_are_saved_and_grouped(self):
        phone_id = self.create("shelter_phone_only", address="")
        email_id = self.create("control_email_only")
        self.assertIsNone(self.stored(phone_id, "email"))
        self.assertIsNone(self.stored(email_id, "phone"))
        text = self.page_text(self.owner.get("/contacts"))
        for key in ("shelter_phone_only", "control_email_only"):
            self.assertIn(self.contacts[key]["category"], text)
            self.assertIn(self.contacts[key]["name"], text)
        self.assertLess(text.index("Animal Control"), text.index("Animal Shelter"))

    def test_tc_301_address_saved_and_shown_on_form_detail_and_list(self):
        row = self.contacts["vet_full"]
        contact_id = self.create("vet_full")
        self.assertEqual(self.stored(contact_id, "address"), row["address"])
        self.assertIn(row["address"], self.page_text(self.owner.get(f"/contacts/{contact_id}")))
        self.assertIn(row["address"], self.page_text(self.owner.get("/contacts")))
        edit = self.owner.get(f"/contacts/{contact_id}/edit")
        self.assertEqual(self.control_value(edit, "address"), row["address"])
        self.assertIn('name="address"', self.owner.get("/contacts/new").get_data(as_text=True))

    def test_tc_301_address_is_optional_and_255_characters_is_allowed(self):
        blank_id = self.create("vet_full", address="")
        self.assertIsNone(self.stored(blank_id, "address"))
        long_id = self.create("shelter_phone_only", address="a" * 255)
        self.assertEqual(self.stored(long_id, "address"), "a" * 255)

    def test_tc_302_edit_persists_after_reopening(self):
        contact_id = self.create("vet_full")
        new_address = "101 Updated Synthetic Way, Testville"
        response = self.post(self.owner, f"/contacts/{contact_id}/edit", self.contact_values(
            "vet_full", name="Updated Vet", phone="555-0113", address=new_address))
        self.assertEqual(response.status_code, 302)
        text = self.page_text(self.owner.get(f"/contacts/{contact_id}"))
        self.assertIn("Updated Vet", text)
        self.assertIn("555-0113", text)
        self.assertEqual(self.stored(contact_id, "address"), new_address)

    def test_tc_302_invalid_new_contact_shows_error_and_saves_nothing(self):
        before = self.contact_count()
        for case in self.invalid["contact"]:
            with self.subTest(case=case["id"]):
                values = self.contact_values("vet_full", **{case["field"]:
                                                            expand_value(case["value"])})
                response = self.post(self.owner, "/contacts/new", values)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.contact_count(), before)

    def test_tc_302_requires_phone_or_email(self):
        before = self.contact_count()
        response = self.post(self.owner, "/contacts/new",
                             self.contact_values("vet_full", phone="", email=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Enter a phone number or an email address.", self.page_text(response))
        self.assertEqual(self.contact_count(), before)

    def test_tc_302_invalid_edit_leaves_contact_unchanged(self):
        contact_id = self.seed_contact("vet_full")
        before = self.snapshot(contact_id)
        response = self.post(self.owner, f"/contacts/{contact_id}/edit",
                             self.contact_values("vet_full", name=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Name is required.", self.page_text(response))
        self.assertEqual(self.snapshot(contact_id), before)

    def test_tc_302_delete_removes_contact(self):
        contact_id = self.seed_contact("vet_full")
        self.assertEqual(self.owner.get(f"/contacts/{contact_id}/delete").status_code, 200)
        self.assertIsNotNone(self.snapshot(contact_id))
        self.assertEqual(self.post(self.owner, f"/contacts/{contact_id}/delete").status_code, 302)
        self.assertIsNone(self.snapshot(contact_id))
        self.assertEqual(self.owner.get(f"/contacts/{contact_id}").status_code, 404)

    def test_tc_303_other_user_cannot_view_edit_or_delete(self):
        contact_id = self.seed_contact("vet_full")
        before = self.snapshot(contact_id)
        for route in (f"/contacts/{contact_id}", f"/contacts/{contact_id}/edit",
                      f"/contacts/{contact_id}/delete"):
            with self.subTest(route=route):
                self.assertEqual(self.other.get(route).status_code, 404)
        edit = self.post(self.other, f"/contacts/{contact_id}/edit",
                         self.contact_values("other_contact"))
        self.assertEqual(edit.status_code, 404)
        delete = self.post(self.other, f"/contacts/{contact_id}/delete")
        self.assertEqual(delete.status_code, 404)
        self.assertEqual(self.snapshot(contact_id), before)
        self.assertNotIn(self.contacts["vet_full"]["name"].encode(),
                         self.other.get("/contacts").data)

    def test_tc_303_guest_is_sent_to_login(self):
        contact_id = self.seed_contact("vet_full")
        before = self.snapshot(contact_id)
        for route in (f"/contacts/{contact_id}", f"/contacts/{contact_id}/edit",
                      f"/contacts/{contact_id}/delete"):
            with self.subTest(route=route):
                self.assert_redirects_to_login(self.guest.get(route))
        self.assert_redirects_to_login(self.post(self.guest, f"/contacts/{contact_id}/delete"))
        self.assertEqual(self.snapshot(contact_id), before)


if __name__ == "__main__":
    unittest.main()
