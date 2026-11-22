"""Load and validate Sprint 3 test data (standard library only).

A file in fixtures/sprint3/examples/ takes priority over the default of the same name.
Invalid data raises FixtureError so a bad example can never silently change a test.
"""

import json
import re
from datetime import date
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "sprint3"
FIXTURE_NAMES = ("users", "pets", "contacts", "password_reset_cases", "invalid_inputs")

EMAIL_RE = re.compile(r"^[^@\s]+@example\.test$")
PHONE_RE = re.compile(r"^555-01\d\d$")
CHIP_RE = re.compile(r"^[A-Za-z0-9]{9,15}$")

USER_FIELDS = {"key", "email", "password", "display_name", "full_name", "phone"}
UPDATE_FIELDS = {"display_name", "full_name", "phone", "email"}
PET_FIELDS = {
    "key", "owner", "name", "species", "breed", "birth_date", "notes", "sex",
    "height_inches", "weight_lbs", "colors", "markings", "microchip_status",
    "microchip_number",
}
CONTACT_FIELDS = {"key", "owner", "category", "name", "phone", "email", "address", "notes"}
REQUIRED_USERS = {"owner", "other"}
REQUIRED_PETS = {
    "full_profile", "second_pet", "other_pet", "special_curly", "special_straight",
    "special_sql",
}
REQUIRED_CONTACTS = {"vet_full", "shelter_phone_only", "control_email_only", "other_contact"}


class FixtureError(ValueError):
    """A fixture file is missing, malformed, or breaks a data rule."""


def _check(condition, message):
    if not condition:
        raise FixtureError(message)


def _fields(row, expected, label):
    _check(isinstance(row, dict), f"{label}: expected an object")
    _check(set(row) == expected, f"{label}: fields differ: {sorted(set(row) ^ expected)}")


def _unique(values, label):
    values = list(values)
    _check(len(values) == len(set(values)), f"{label}: duplicate values")


def _rows(data, key, label):
    _check(isinstance(data, dict), f"{label}: expected an object")
    _check(isinstance(data.get(key), list) and data[key], f"{label}: {key} must be a list")
    return data[key]


def _email(value, label):
    _check(isinstance(value, str) and EMAIL_RE.match(value), f"{label}: not @example.test")


def _phone(value, label):
    _check(isinstance(value, str) and PHONE_RE.match(value), f"{label}: not 555-01xx")


def _max_len(row, field, limit, label):
    value = row[field]
    _check(value is None or (isinstance(value, str) and len(value) <= limit),
           f"{label}: {field} over {limit}")


def _number(row, field, limit, label):
    value = row[field]
    if value is None:
        return
    _check(isinstance(value, (int, float)) and not isinstance(value, bool)
           and 0 < value <= limit, f"{label}: {field} out of range")


def validate_users(data):
    rows = _rows(data, "users", "users")
    for row in rows:
        label = f"users:{row.get('key') if isinstance(row, dict) else row}"
        _fields(row, USER_FIELDS, label)
        _email(row["email"], label)
        _phone(row["phone"], label)
        _check(len(row["password"]) >= 8, f"{label}: password too short")
    _unique((r["key"] for r in rows), "users.key")
    _unique((r["email"] for r in rows), "users.email")
    _check(REQUIRED_USERS <= {r["key"] for r in rows}, "users: required keys missing")
    update = data.get("account_update")
    _fields(update, UPDATE_FIELDS, "account_update")
    _email(update["email"], "account_update")
    _phone(update["phone"], "account_update")
    _check(update["email"] not in {r["email"] for r in rows},
           "account_update: email already used")


def validate_pets(data):
    rows = _rows(data, "pets", "pets")
    for row in rows:
        label = f"pets:{row.get('key') if isinstance(row, dict) else row}"
        _fields(row, PET_FIELDS, label)
        _check(row["name"] and row["species"], f"{label}: name and species required")
        _check(row["sex"] in (None, "male", "female", "unknown"), f"{label}: bad sex")
        _number(row, "height_inches", 120, label)
        _number(row, "weight_lbs", 500, label)
        _max_len(row, "colors", 100, label)
        _max_len(row, "markings", 255, label)
        if row["birth_date"] is not None:
            try:
                born = date.fromisoformat(row["birth_date"])
            except (TypeError, ValueError) as exc:
                raise FixtureError(f"{label}: bad birth_date") from exc
            _check(born <= date.today(), f"{label}: future birth_date")
        status, number = row["microchip_status"], row["microchip_number"]
        _check(status in ("unknown", "chipped", "not_chipped"), f"{label}: bad chip status")
        if status == "chipped":
            _check(isinstance(number, str) and CHIP_RE.match(number), f"{label}: bad chip")
        else:
            _check(number is None, f"{label}: chip number without chipped status")
    _unique((r["key"] for r in rows), "pets.key")
    _check(REQUIRED_PETS <= {r["key"] for r in rows}, "pets: required keys missing")


def validate_contacts(data):
    rows = _rows(data, "contacts", "contacts")
    for row in rows:
        label = f"contacts:{row.get('key') if isinstance(row, dict) else row}"
        _fields(row, CONTACT_FIELDS, label)
        _check(row["category"] and row["name"], f"{label}: category and name required")
        _check(row["phone"] or row["email"], f"{label}: phone or email required")
        if row["phone"] is not None:
            _phone(row["phone"], label)
        if row["email"] is not None:
            _email(row["email"], label)
        _max_len(row, "address", 255, label)
    _unique((r["key"] for r in rows), "contacts.key")
    _check(REQUIRED_CONTACTS <= {r["key"] for r in rows}, "contacts: required keys missing")


def validate_password_reset_cases(data):
    _check(isinstance(data, dict), "password_reset_cases: expected an object")
    expected = {"known_user", "unknown_email", "new_password", "invalid_passwords",
                "invalid_tokens"}
    _fields(data, expected, "password_reset_cases")
    _email(data["unknown_email"], "password_reset_cases.unknown_email")
    _check(len(data["new_password"]) >= 8, "password_reset_cases: new_password too short")
    cases = _rows(data, "invalid_passwords", "password_reset_cases")
    for case in cases:
        _fields(case, {"id", "password", "confirm_password", "error_field"},
                f"invalid_passwords:{case.get('id') if isinstance(case, dict) else case}")
    _unique((c["id"] for c in cases), "invalid_passwords.id")
    tokens = _rows(data, "invalid_tokens", "password_reset_cases")
    _unique(tokens, "invalid_tokens")


def validate_invalid_inputs(data):
    _check(isinstance(data, dict), "invalid_inputs: expected an object")
    _fields(data, {"pet", "contact", "account", "unsafe_next", "safe_next"}, "invalid_inputs")
    for group in ("pet", "contact", "account"):
        cases = _rows(data, group, "invalid_inputs")
        for case in cases:
            _check(isinstance(case, dict) and {"id", "field", "value"} <= set(case)
                   and set(case) <= {"id", "field", "value", "extra"},
                   f"invalid_inputs.{group}: bad case {case}")
            expand_value(case["value"])
        _unique((c["id"] for c in cases), f"invalid_inputs.{group}.id")
    for group in ("unsafe_next", "safe_next"):
        values = _rows(data, group, "invalid_inputs")
        _check(all(isinstance(v, str) and v for v in values), f"{group}: strings required")
        _unique(values, group)
    _check(all(v.startswith("/") and not v.startswith("//") for v in data["safe_next"]),
           "safe_next: must be same-site paths")


VALIDATORS = {
    "users": validate_users,
    "pets": validate_pets,
    "contacts": validate_contacts,
    "password_reset_cases": validate_password_reset_cases,
    "invalid_inputs": validate_invalid_inputs,
}


def expand_value(value):
    """Return a case value, expanding {"repeat": "x", "times": n} for long strings."""
    if isinstance(value, str):
        return value
    _check(isinstance(value, dict) and set(value) == {"repeat", "times"}
           and isinstance(value["repeat"], str) and isinstance(value["times"], int),
           f"bad case value: {value}")
    return value["repeat"] * value["times"]


def fixture_path(name, root=FIXTURE_ROOT):
    """Return the example file when one exists, otherwise the default file."""
    _check(name in VALIDATORS, f"unknown fixture: {name}")
    root = Path(root)
    example = root / "examples" / f"{name}.json"
    return example if example.is_file() else root / f"{name}.json"


def load_fixture(name, root=FIXTURE_ROOT):
    path = fixture_path(name, root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureError(f"{path}: {exc}") from exc
    VALIDATORS[name](data)
    return data


def load_all(root=FIXTURE_ROOT):
    """Load every fixture and check that owners refer to known users."""
    data = {name: load_fixture(name, root) for name in FIXTURE_NAMES}
    users = {row["key"] for row in data["users"]["users"]}
    for group in ("pets", "contacts"):
        for row in data[group][group]:
            _check(row["owner"] in users, f"{group}:{row['key']}: unknown owner")
    _check(data["password_reset_cases"]["known_user"] in users,
           "password_reset_cases: unknown known_user")
    known = {row["email"] for row in data["users"]["users"]}
    _check(data["password_reset_cases"]["unknown_email"] not in known,
           "password_reset_cases: unknown_email belongs to a user")
    return data


def by_key(rows):
    return {row["key"]: row for row in rows}
