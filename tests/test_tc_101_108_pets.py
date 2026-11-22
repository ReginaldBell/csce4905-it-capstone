"""TC-101 to TC-108: pet profile, ownership, editing, deletion, and photo privacy."""

import io
import re
import unittest
from datetime import date, datetime, timedelta

from extensions import db
from models import Pet
from sprint3_base import MISSING, PET_FORM_FIELDS, PNG_BYTES, Sprint3TestCase


def months_ago(months, today=None):
    """A birth date exactly N calendar months ago, avoiding short-month clamping."""
    today = today or date.today()
    index = today.year * 12 + today.month - 1 - months
    return date(index // 12, index % 12 + 1, min(today.day, 28))


class PetTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.login_both()

    def create(self, key="full_profile", client=None, **changes):
        response = self.post(client or self.owner, "/pets/new", self.pet_values(key, **changes))
        self.assertEqual(response.status_code, 302, "pet was not saved")
        return int(response.headers["Location"].rstrip("/").rsplit("/", 1)[-1])

    def stored(self, pet_id, field):
        with self.app.app_context():
            return getattr(db.session.get(Pet, pet_id), field, MISSING)

    def upload(self, pet_id, content=PNG_BYTES):
        values = self.pet_values("second_pet", name="Photo Pet")
        values["photo"] = (io.BytesIO(content), "pet.png", "image/png")
        response = self.post(self.owner, f"/pets/{pet_id}/edit", values)
        self.assertEqual(response.status_code, 302)
        return self.stored(pet_id, "photo_path")

    def age_for(self, birth_date):
        pet_id = self.seed_pet(birth_date=birth_date)
        age = self.stored(pet_id, "age_display")
        self.assertIsNot(age, MISSING, "Pet.age_display is required by the contract")
        return age

    # TC-101 -----------------------------------------------------------------

    def test_tc_101_full_profile_saves_and_matches(self):
        pet_id = self.create()
        row = self.pets["full_profile"]
        for field in ("name", "species", "breed", "notes", "sex", "height_inches", "weight_lbs",
                      "colors", "markings", "microchip_status", "microchip_number"):
            with self.subTest(field=field):
                self.assertEqual(self.stored(pet_id, field), row[field])
        self.assertEqual(self.stored(pet_id, "birth_date"),
                         date.fromisoformat(row["birth_date"]))
        self.assertEqual(self.stored(pet_id, "owner_id"), self.user_ids["owner"])

    def test_tc_101_add_form_shows_every_field(self):
        response = self.owner.get("/pets/new")
        for field in PET_FORM_FIELDS:
            with self.subTest(field=field):
                self.assertIn(f'name="{field}"', response.get_data(as_text=True))

    def test_tc_101_detail_page_shows_all_saved_fields_and_age(self):
        pet_id = self.create()
        row = self.pets["full_profile"]
        text = self.page_text(self.owner.get(f"/pets/{pet_id}")).lower()
        for field in ("name", "species", "breed", "notes", "sex", "colors", "markings",
                      "microchip_number"):
            with self.subTest(field=field):
                self.assertIn(str(row[field]).lower(), text)
        self.assertIn(str(row["height_inches"]), text)
        self.assertIn(str(row["weight_lbs"]), text)
        age = self.stored(pet_id, "age_display")
        self.assertIsInstance(age, str)
        self.assertIn(age.lower(), text)

    def test_tc_101_edit_form_is_prefilled(self):
        pet_id = self.create()
        row = self.pets["full_profile"]
        page = self.owner.get(f"/pets/{pet_id}/edit")
        for field in ("sex", "colors", "markings", "microchip_status", "microchip_number"):
            with self.subTest(field=field):
                self.assertEqual(self.control_value(page, field), row[field])
        for field in ("height_inches", "weight_lbs"):
            with self.subTest(field=field):
                self.assertEqual(float(self.control_value(page, field)), row[field])

    def test_tc_101_optional_new_fields_can_be_blank(self):
        pet_id = self.create("second_pet", sex="", microchip_status="unknown")
        for field in ("sex", "height_inches", "weight_lbs", "colors", "markings",
                      "microchip_number"):
            with self.subTest(field=field):
                self.assertIsNone(self.stored(pet_id, field))
        self.assertEqual(self.stored(pet_id, "microchip_status"), "unknown")

    def test_tc_101_microchip_status_defaults_to_unknown(self):
        pet_id = self.seed_pet()
        self.assertEqual(self.stored(pet_id, "microchip_status"), "unknown")

    def test_tc_101_age_none_without_birth_date(self):
        self.assertIsNone(self.age_for(None))

    def test_tc_101_age_under_one_month(self):
        self.assertEqual(self.age_for(date.today()), "Under 1 month")
        self.assertEqual(self.age_for(date.today() - timedelta(days=5)), "Under 1 month")

    def test_tc_101_age_in_months(self):
        # The contract writes "N month(s)"; either that literal or normal plurals is accepted.
        self.assertRegex(self.age_for(months_ago(1)), r"^1 month(\(s\))?$")
        self.assertRegex(self.age_for(months_ago(5)), r"^5 month(s|\(s\))$")

    def test_tc_101_age_in_years(self):
        self.assertRegex(self.age_for(months_ago(12)), r"^1 year(\(s\))?$")
        self.assertRegex(self.age_for(months_ago(36)), r"^3 year(s|\(s\))$")

    def test_tc_101_age_in_years_and_months(self):
        self.assertRegex(self.age_for(months_ago(27)), r"^2 year(s|\(s\)), 3 month(s|\(s\))$")

    def test_tc_101_age_display_is_read_only(self):
        pet_id = self.seed_pet(birth_date=months_ago(5))
        with self.app.app_context():
            pet = db.session.get(Pet, pet_id)
            with self.assertRaises(AttributeError):
                pet.age_display = "forged"

    # TC-102 -----------------------------------------------------------------

    def test_tc_102_name_and_species_are_required(self):
        before = self.pet_count()
        for blanks, messages in (
            ({"name": ""}, ["Name is required."]),
            ({"species": ""}, ["Species is required."]),
            ({"name": "", "species": ""}, ["Name is required.", "Species is required."]),
        ):
            with self.subTest(blanks=blanks):
                values = {"name": "Named", "species": "Dog", **blanks}
                response = self.post(self.owner, "/pets/new", values)
                self.assertEqual(response.status_code, 200)
                for message in messages:
                    self.assertIn(message, self.page_text(response))
                self.assertEqual(self.pet_count(), before)

    # TC-103 -----------------------------------------------------------------

    def test_tc_103_each_account_sees_only_its_pets_and_photo(self):
        (self.upload_dir / "a1.png").write_bytes(PNG_BYTES)
        first = self.seed_pet("owner", "Alpha One", photo_path="uploads/a1.png")
        second = self.seed_pet("owner", "Alpha Two")
        third = self.seed_pet("other", "Bravo One")
        owner_list = self.owner.get("/pets").get_data(as_text=True)
        other_list = self.other.get("/pets").get_data(as_text=True)
        self.assertIn("Alpha One", owner_list)
        self.assertIn("Alpha Two", owner_list)
        self.assertNotIn("Bravo One", owner_list)
        self.assertIn("Bravo One", other_list)
        self.assertNotIn("Alpha", other_list)
        for pet_id, name in ((first, "Alpha One"), (second, "Alpha Two")):
            self.assertIn(name, self.owner.get(f"/pets/{pet_id}").get_data(as_text=True))
        self.assertIn("Bravo One", self.other.get(f"/pets/{third}").get_data(as_text=True))
        self.assertIn("uploads/a1.png", self.owner.get(f"/pets/{first}").get_data(as_text=True))
        self.assertEqual(self.owner.get("/static/uploads/a1.png").data, PNG_BYTES)

    # TC-104 -----------------------------------------------------------------

    def test_tc_104_other_user_gets_404_and_record_is_unchanged(self):
        pet_id = self.seed_pet(name="Guarded")
        before = self.pet_snapshot(pet_id)
        for route in (f"/pets/{pet_id}", f"/pets/{pet_id}/edit", f"/pets/{pet_id}/delete"):
            with self.subTest(route=route):
                self.assertEqual(self.other.get(route).status_code, 404)
        edit = self.post(self.other, f"/pets/{pet_id}/edit", {"name": "Stolen", "species": "Cat"})
        self.assertEqual(edit.status_code, 404)
        self.assertEqual(self.post(self.other, f"/pets/{pet_id}/delete").status_code, 404)
        self.assertEqual(self.pet_snapshot(pet_id), before)

    def test_tc_104_guest_is_sent_to_login_and_record_is_unchanged(self):
        pet_id = self.seed_pet(name="Guarded")
        before = self.pet_snapshot(pet_id)
        for route in (f"/pets/{pet_id}", f"/pets/{pet_id}/edit", f"/pets/{pet_id}/delete"):
            with self.subTest(route=route):
                self.assert_redirects_to_login(self.guest.get(route))
        self.assert_redirects_to_login(self.post(
            self.guest, f"/pets/{pet_id}/edit", {"name": "Stolen", "species": "Cat"}))
        self.assert_redirects_to_login(self.post(self.guest, f"/pets/{pet_id}/delete"))
        self.assertEqual(self.pet_snapshot(pet_id), before)

    # TC-105 -----------------------------------------------------------------

    def test_tc_105_edit_persists_and_updates_timestamp(self):
        pet_id = self.create()
        old = datetime(2020, 1, 1)
        with self.app.app_context():
            Pet.query.filter_by(id=pet_id).update({"updated_at": old})
            db.session.commit()
        changes = {"name": "Juniper Two", "colors": "Slate", "markings": "Star on chest",
                   "sex": "unknown", "height_inches": "24", "weight_lbs": "62.5"}
        response = self.post(self.owner, f"/pets/{pet_id}/edit",
                             self.pet_values("full_profile", **changes))
        self.assertEqual(response.status_code, 302)
        text = self.page_text(self.owner.get(f"/pets/{pet_id}"))
        self.assertIn("Juniper Two", text)
        for field in ("colors", "markings", "sex"):
            self.assertEqual(self.stored(pet_id, field), changes[field])
        self.assertEqual(self.stored(pet_id, "height_inches"), 24.0)
        self.assertEqual(self.stored(pet_id, "weight_lbs"), 62.5)
        self.assertGreater(self.stored(pet_id, "updated_at"), old)

    def test_tc_105_microchip_number_cleared_unless_chipped(self):
        for status in ("unknown", "not_chipped"):
            with self.subTest(status=status):
                pet_id = self.create()
                self.assertEqual(self.stored(pet_id, "microchip_number"),
                                 self.pets["full_profile"]["microchip_number"])
                response = self.post(self.owner, f"/pets/{pet_id}/edit", self.pet_values(
                    "full_profile", microchip_status=status))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.stored(pet_id, "microchip_status"), status)
                self.assertIsNone(self.stored(pet_id, "microchip_number"))

    # TC-106 -----------------------------------------------------------------

    def test_tc_106_cancel_keeps_pet_and_confirm_removes_it(self):
        pet_id = self.seed_pet(name="Keep Or Delete")
        page = self.owner.get(f"/pets/{pet_id}/delete")
        self.assertEqual(page.status_code, 200)
        self.assertIn(f'href="/pets/{pet_id}"', page.get_data(as_text=True))
        self.assertEqual(self.owner.get(f"/pets/{pet_id}").status_code, 200)
        self.assertIsNotNone(self.pet_snapshot(pet_id))
        response = self.post(self.owner, f"/pets/{pet_id}/delete")
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.pet_snapshot(pet_id))
        self.assertEqual(self.owner.get(f"/pets/{pet_id}").status_code, 404)
        self.owner.get("/pets")  # The first load shows the "was deleted" message.
        self.assertNotIn(b"Keep Or Delete", self.owner.get("/pets").data)

    # TC-107 -----------------------------------------------------------------

    def test_tc_107_private_photo_opens_only_for_owner(self):
        pet_id = self.seed_pet(name="Photo Pet")
        path = self.upload(pet_id)
        url = f"/static/{path}"
        owner_response = self.owner.get(url)
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response.data, PNG_BYTES)
        owner_response.close()
        self.assertEqual(self.other.get(url).status_code, 404)
        self.assert_redirects_to_login(self.guest.get(url))

    def test_tc_107_replaced_photo_old_url_is_dead_for_everyone(self):
        pet_id = self.seed_pet(name="Photo Pet")
        old_path = self.upload(pet_id, PNG_BYTES + b"old")
        new_path = self.upload(pet_id, PNG_BYTES + b"new")
        self.assertNotEqual(old_path, new_path)
        self.assertFalse((self.upload_dir / old_path.split("/", 1)[1]).exists())
        old_url, new_url = f"/static/{old_path}", f"/static/{new_path}"
        self.assertEqual(self.owner.get(old_url).status_code, 404)
        self.assertEqual(self.other.get(old_url).status_code, 404)
        self.assert_redirects_to_login(self.guest.get(old_url))
        current = self.owner.get(new_url)
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data, PNG_BYTES + b"new")
        current.close()
        self.assertEqual(self.other.get(new_url).status_code, 404)
        self.assert_redirects_to_login(self.guest.get(new_url))

    # TC-108 -----------------------------------------------------------------

    def test_tc_108_future_birth_date_rejected_then_valid_date_saved(self):
        before = self.pet_count()
        values = {"name": "Future Pet", "species": "Dog", "birth_date": "2099-01-01"}
        response = self.post(self.owner, "/pets/new", values)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Birth date cannot be in the future.", self.page_text(response))
        self.assertEqual(self.pet_count(), before)
        response = self.post(self.owner, "/pets/new", {**values, "birth_date": "2020-01-01"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.pet_count(), before + 1)
        with self.app.app_context():
            saved = Pet.query.filter_by(name="Future Pet").one()
            self.assertEqual(saved.birth_date, date(2020, 1, 1))


if __name__ == "__main__":
    unittest.main()
