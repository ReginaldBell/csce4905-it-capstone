# Sprint 3 example data

Put the example data files for Sprint 3 in this folder. A file here replaces the file of
the same name one level up, for that file only. Anything not provided keeps using the
synthetic default.

Accepted names: `users.json`, `pets.json`, `contacts.json`, `password_reset_cases.json`,
`invalid_inputs.json`.

Rules checked by `tests/sprint3_data.py` (a bad file fails loudly; it is never ignored):

- Synthetic data only. Emails end in `@example.test`; phones look like `555-01xx`.
- Keep the same JSON shape as the default file. Keys, emails, and case IDs must be unique.
- `users.json`: `{"users": [{key, email, password, display_name, full_name, phone}],
  "account_update": {display_name, full_name, phone, email}}`. Needs keys `owner`, `other`.
- `pets.json`: `{"pets": [{key, owner, name, species, breed, birth_date, notes, sex,
  height_inches, weight_lbs, colors, markings, microchip_status, microchip_number}]}`.
  Needs keys `full_profile`, `second_pet`, `other_pet`, `special_curly`,
  `special_straight`, `special_sql`.
- `contacts.json`: `{"contacts": [{key, owner, category, name, phone, email, address,
  notes}]}`. Needs keys `vet_full`, `shelter_phone_only`, `control_email_only`,
  `other_contact`.
- `password_reset_cases.json`: `{known_user, unknown_email, new_password,
  invalid_passwords: [{id, password, confirm_password, error_field}], invalid_tokens: []}`.
- `invalid_inputs.json`: `{pet: [], contact: [], account: [], unsafe_next: [],
  safe_next: []}`. Case entries are `{id, field, value, extra?}`. A long `value` can be
  written as `{"repeat": "x", "times": 101}`.

`owner` values must match a `key` in the active `users.json`.
