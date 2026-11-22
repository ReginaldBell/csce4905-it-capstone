"""TC-1001 and TC-1003 to TC-1006: password storage, ownership, validation, persistence."""

import unittest
from datetime import date

from sqlalchemy import inspect

from extensions import db
from models import Pet, User
from sprint3_base import MISSING, Sprint3TestCase

NEW_EMAIL = "hash.check@example.test"
NEW_PASSWORD = "SyntheticPass401!"


class DataIntegrityTests(Sprint3TestCase):
    def create(self, client, key, **changes):
        response = self.post(client, "/pets/new", self.pet_values(key, **changes))
        self.assertEqual(response.status_code, 302, "pet was not saved")
        return int(response.headers["Location"].rstrip("/").rsplit("/", 1)[-1])

    def test_tc_1001_registered_password_is_hashed_and_verified(self):
        response = self.post(self.guest, "/register", {
            "email": NEW_EMAIL, "password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = User.query.filter_by(email=NEW_EMAIL).one()
            self.assertNotEqual(user.password_hash, NEW_PASSWORD)
            self.assertNotIn(NEW_PASSWORD, user.password_hash)
            self.assertRegex(user.password_hash, r"^(scrypt|pbkdf2):")
            self.assertTrue(user.check_password(NEW_PASSWORD))
            self.assertFalse(user.check_password("WrongPass999!"))

    def test_tc_1001_login_accepts_correct_and_rejects_wrong_password(self):
        self.assertEqual(self.login(self.guest, password="WrongPass999!").status_code, 200)
        self.assert_redirects_to_login(self.guest.get("/pets"))
        self.assertEqual(self.login(self.guest).status_code, 302)
        self.assertEqual(self.guest.get("/pets").status_code, 200)

    def test_tc_1003_new_pet_uses_current_owner_even_if_forged(self):
        self.login_both()
        response = self.post(self.other, "/pets/new", {
            "name": "Forged Owner", "species": "Dog", "owner_id": str(self.user_ids["owner"])})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(Pet.query.filter_by(name="Forged Owner").one().owner_id,
                             self.user_ids["other"])

    def test_tc_1003_other_account_cannot_read_or_change_pet(self):
        self.login_both()
        pet_id = self.seed_pet(name="Owned Pet")
        before = self.pet_snapshot(pet_id)
        self.assertEqual(self.other.get(f"/pets/{pet_id}").status_code, 404)
        self.assertNotIn(b"Owned Pet", self.other.get("/pets").data)
        response = self.post(self.other, f"/pets/{pet_id}/edit", {"name": "X", "species": "Cat"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.post(self.other, f"/pets/{pet_id}/delete").status_code, 404)
        self.assertEqual(self.pet_snapshot(pet_id), before)

    def test_tc_1004_valid_data_saves(self):
        self.login(self.owner)
        before = self.pet_count()
        self.create(self.owner, "full_profile")
        self.assertEqual(self.pet_count(), before + 1)

    def test_tc_1004_missing_required_fields_create_no_pet(self):
        self.login(self.owner)
        before = self.pet_count()
        for blanks in ({"name": ""}, {"species": ""}, {"name": "   ", "species": "   "}):
            with self.subTest(blanks=blanks):
                response = self.post(self.owner, "/pets/new",
                                     self.pet_values("full_profile", **blanks))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.pet_count(), before)

    def test_tc_1004_future_birth_date_creates_no_pet(self):
        self.login(self.owner)
        before = self.pet_count()
        response = self.post(self.owner, "/pets/new",
                             self.pet_values("full_profile", birth_date="2099-01-01"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.pet_count(), before)

    def test_tc_1005_values_survive_reload_and_stay_per_account(self):
        self.login_both()
        first = self.create(self.owner, "full_profile")
        second = self.create(self.owner, "second_pet")
        third = self.create(self.other, "other_pet")
        with self.app.app_context():
            db.session.remove()
            owner_ids = {p.id for p in Pet.query.filter_by(owner_id=self.user_ids["owner"])}
            other_ids = {p.id for p in Pet.query.filter_by(owner_id=self.user_ids["other"])}
            self.assertEqual(owner_ids, {first, second})
            self.assertEqual(other_ids, {third})
            saved = db.session.get(Pet, first)
            row = self.pets["full_profile"]
            self.assertEqual(saved.name, row["name"])
            self.assertEqual(saved.birth_date, date.fromisoformat(row["birth_date"]))
            for field in ("sex", "height_inches", "weight_lbs", "colors", "markings",
                          "microchip_status", "microchip_number"):
                self.assertEqual(getattr(saved, field, MISSING), row[field], field)
        owner_page = self.owner.get("/pets").get_data(as_text=True)
        other_page = self.other.get("/pets").get_data(as_text=True)
        self.assertIn(self.pets["full_profile"]["name"], owner_page)
        self.assertNotIn(self.pets["other_pet"]["name"], owner_page)
        self.assertIn(self.pets["other_pet"]["name"], other_page)
        self.assertNotIn(self.pets["full_profile"]["name"], other_page)

    def test_tc_1006_special_character_names_are_kept_exactly(self):
        self.login(self.owner)
        for key in ("special_curly", "special_straight", "special_sql"):
            with self.subTest(key=key):
                name = self.pets[key]["name"]
                response = self.post(self.owner, "/pets/new", {"name": name, "species": "Cat"})
                self.assertEqual(response.status_code, 302)
                pet_id = int(response.headers["Location"].rsplit("/", 1)[-1])
                with self.app.app_context():
                    db.session.remove()
                    self.assertEqual(db.session.get(Pet, pet_id).name, name)
                    self.assertEqual(Pet.query.filter_by(name=name).one().id, pet_id)
                self.assertIn(name, self.page_text(self.owner.get(f"/pets/{pet_id}")))

    def test_tc_1006_sql_text_is_stored_as_a_value(self):
        self.login(self.owner)
        before = self.pet_count()
        name = self.pets["special_sql"]["name"]
        self.post(self.owner, "/pets/new", {"name": name, "species": "Other"})
        with self.app.app_context():
            self.assertIn("pets", inspect(db.engine).get_table_names())
        self.assertEqual(self.pet_count(), before + 1)


if __name__ == "__main__":
    unittest.main()
