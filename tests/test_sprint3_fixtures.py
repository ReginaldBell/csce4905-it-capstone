"""Fixture and loader tests. These do not depend on Sprint 3 application code."""

import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import sprint3_data as data


class FixtureSetTests(unittest.TestCase):
    def test_all_fixtures_load_and_cross_reference(self):
        loaded = data.load_all()
        self.assertEqual(set(loaded), set(data.FIXTURE_NAMES))

    def test_examples_folder_and_readme_exist(self):
        readme = data.FIXTURE_ROOT / "examples" / "README.md"
        self.assertTrue(readme.is_file())
        text = readme.read_text(encoding="utf-8")
        for name in data.FIXTURE_NAMES:
            self.assertIn(f"{name}.json", text)

    def test_all_contact_data_is_synthetic(self):
        for name in data.FIXTURE_NAMES:
            raw = data.fixture_path(name).read_text(encoding="utf-8")
            for email in re.findall(r"[\w.+-]+@[\w.-]+", raw):
                self.assertTrue(email.endswith("@example.test"), email)
            for phone in re.findall(r"\b\d{3}-\d{4}\b", raw):
                self.assertRegex(phone, r"^555-01\d\d$")

    def test_expand_value(self):
        self.assertEqual(data.expand_value("abc"), "abc")
        self.assertEqual(len(data.expand_value({"repeat": "x", "times": 101})), 101)
        with self.assertRaises(data.FixtureError):
            data.expand_value({"repeat": "x"})


class FixtureValidationTests(unittest.TestCase):
    def assert_rejected(self, name, change):
        loaded = copy.deepcopy(data.load_fixture(name))
        change(loaded)
        with self.assertRaises(data.FixtureError):
            data.VALIDATORS[name](loaded)

    def test_rejects_duplicate_keys_and_emails(self):
        def dup_user_key(d):
            d["users"][1]["key"] = d["users"][0]["key"]

        def dup_email(d):
            d["users"][1]["email"] = d["users"][0]["email"]

        def dup_pet(d):
            d["pets"][1]["key"] = d["pets"][0]["key"]

        def dup_contact(d):
            d["contacts"][1]["key"] = d["contacts"][0]["key"]

        self.assert_rejected("users", dup_user_key)
        self.assert_rejected("users", dup_email)
        self.assert_rejected("pets", dup_pet)
        self.assert_rejected("contacts", dup_contact)

    def test_rejects_non_synthetic_contact_data(self):
        self.assert_rejected("users", lambda d: d["users"][0].update(email="a@gmail.com"))
        self.assert_rejected("users", lambda d: d["users"][0].update(phone="214-555-1234"))
        self.assert_rejected("contacts", lambda d: d["contacts"][0].update(email="v@real.com"))

    def test_rejects_wrong_shape(self):
        self.assert_rejected("users", lambda d: d["users"][0].pop("phone"))
        self.assert_rejected("pets", lambda d: d["pets"][0].update(surprise=1))
        self.assert_rejected("contacts", lambda d: d.update(contacts=[]))
        self.assert_rejected("invalid_inputs", lambda d: d.pop("pet"))
        self.assert_rejected("password_reset_cases", lambda d: d.pop("new_password"))

    def test_rejects_values_that_break_contract_rules(self):
        for change in (
            {"sex": "other"}, {"height_inches": 0}, {"height_inches": 121},
            {"weight_lbs": 501}, {"colors": "c" * 101}, {"markings": "m" * 256},
            {"microchip_status": "maybe"}, {"microchip_number": "SHORT"},
            {"microchip_number": None}, {"birth_date": "2099-01-01"},
            {"birth_date": "not-a-date"},
        ):
            with self.subTest(change=change):
                self.assert_rejected("pets", lambda d: d["pets"][0].update(change))

    def test_rejects_chip_number_without_chipped_status(self):
        self.assert_rejected("pets", lambda d: d["pets"][0].update(microchip_status="unknown"))

    def test_rejects_contact_without_phone_or_email(self):
        self.assert_rejected("contacts", lambda d: d["contacts"][0].update(phone=None, email=None))

    def test_rejects_missing_required_record(self):
        self.assert_rejected("pets", lambda d: d.update(
            pets=[p for p in d["pets"] if p["key"] != "special_curly"]))


class ExamplePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "sprint3"
        self.root.mkdir()
        (self.root / "examples").mkdir()
        for name in data.FIXTURE_NAMES:
            shutil.copy(data.FIXTURE_ROOT / f"{name}.json", self.root / f"{name}.json")

    def tearDown(self):
        self.tmp.cleanup()

    def write_example(self, name, content):
        path = self.root / "examples" / f"{name}.json"
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    def test_uses_default_without_example(self):
        self.assertEqual(data.fixture_path("pets", self.root), self.root / "pets.json")

    def test_prefers_matching_example_only(self):
        pets = json.loads((self.root / "pets.json").read_text(encoding="utf-8"))
        pets["pets"][0]["name"] = "Example Pet"
        path = self.write_example("pets", pets)
        self.assertEqual(data.fixture_path("pets", self.root), path)
        self.assertEqual(data.load_fixture("pets", self.root)["pets"][0]["name"], "Example Pet")
        self.assertEqual(data.fixture_path("users", self.root), self.root / "users.json")

    def test_invalid_example_fails_instead_of_falling_back(self):
        self.write_example("pets", {"pets": []})
        with self.assertRaises(data.FixtureError):
            data.load_fixture("pets", self.root)

    def test_malformed_json_example_fails(self):
        (self.root / "examples" / "users.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(data.FixtureError):
            data.load_fixture("users", self.root)

    def test_example_with_unknown_owner_fails_cross_check(self):
        pets = json.loads((self.root / "pets.json").read_text(encoding="utf-8"))
        pets["pets"][0]["owner"] = "ghost"
        self.write_example("pets", pets)
        with self.assertRaises(data.FixtureError):
            data.load_all(self.root)


if __name__ == "__main__":
    unittest.main()
