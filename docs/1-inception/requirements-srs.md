# Software Requirements Specification (SRS)

**Phase:** Inception | **Status:** Sprint 2 implementation baseline; sponsor approval _TBD_

**Owner:** _TBD_ | **Recorded:** November 4, 2026

## 1. Purpose and scope

This document specifies the behavior delivered in Pet Finder through Sprint 2 at
`4d51cc3`. It supplements the pending sponsor-facing [Vision & Scope](vision.md).
Requirements below are derived from implemented PR descriptions and review
criteria, not an assertion of sponsor sign-off.

Sprint 1 account and pet-profile functionality remains the foundation. Sprint 2
adds contacts, multi-pet missing reports, status history, generated outreach, and
a stale-pet reminder. See the [delivery/decision record](../project-management/sprint-2-record.md).

The `S2` identifiers distinguish these concrete requirements from unfilled
identifiers in the original document templates.

## 2. Users, environment, and constraints

The primary user is an authenticated pet owner. Agency contacts are records owned
by that user, not agency accounts or system integrations. An unauthenticated visitor
can register or log in.

The delivered environment is a browser, a Flask/Jinja application, SQLAlchemy,
and PostgreSQL 16 in local Docker Compose. JavaScript supplies the selected-date
timezone offset and browser copy/print behavior. Production hosting, service-level
targets, formal browser support, and sponsor-specific constraints remain _TBD_.

## 3. Functional requirements

All rows are required behavior of the delivered Sprint 2 baseline.

| ID | Requirement | Source | Use case |
|---|---|---|---|
| FR-S2-01 | Manage owned contacts through list/view/create/edit/delete; group by category and order names alphabetically; require category/name and at least one valid-format phone/email; enforce column-length limits with inline errors. | PR #13, card 3 | UC-S2-01 |
| FR-S2-02 | Store reports and explicit report-pet links, allowing multiple pets per report while retaining existing users/pets. Preserve a report when a linked pet is deleted. | PR #12, card 4 | UC-S2-02 |
| FR-S2-03 | List/view owned reports and create an open report from at least one owned pet, a required location, optional last-seen time, and notes. Convert selected local time to UTC and reject future values; redirect a user with no pets to add one. | PR #14, card 5 | UC-S2-02 |
| FR-S2-04 | Allow open/found/closed status changes with initial/transition history; set closed_at on closing and clear it when leaving closed; no-op on repeated status. | PR #15, card 11 | UC-S2-03 |
| FR-S2-05 | Generate agency-email subject/body from a report, with an owned-contact picker, copy controls, and encoded mailto when the contact has email. | PR #16, card 6 | UC-S2-04 |
| FR-S2-06 | Generate a phone script for an owned report/contact; show saved phone or a fallback and provide a copy control; preserve shared email selection. | PR #17, card 7 | UC-S2-05 |
| FR-S2-07 | Generate a social caption without needing a contact, with photo-download links and a named fallback for pets without photos. | PR #18, card 8 | UC-S2-06 |
| FR-S2-08 | Generate a printable flyer with all names, deduplicated species, first available photo, last-seen data, a notes excerpt, and reporter email; hide navigation/messages/controls in print. | PR #19, card 9 | UC-S2-07 |
| FR-S2-09 | On successful login, show one sorted informational reminder for the user's pets whose updated_at is strictly older than 90 days; exclude registration and failed login. | PR #20, card 10 | UC-S2-08 |

### Field and state rules

- Contact category: required, at most 50 characters. Name: required, at most 100.
  Phone: optional 7–30-character allowed-format string containing a digit.
  Email: optional format-checked string, at most 255 characters. Phone or email
  must be supplied. Category suggestions do not prohibit custom categories.
- Report location: required, at most 255 characters. Time: optional
  `YYYY-MM-DDTHH:MM`. Offset: date-specific `UTC - local` minutes, inclusive
  `[-840, 720]`. Invalid out-of-range numeric offsets return a field error;
  absent/non-numeric offsets retain the zero fallback.
- Selected pet IDs are deduplicated and filtered to the owner. A forged-only
  selection does not create a report; a mixed selection links only owned pets.
- New reports start `open`. History records actual changes; old reports are not
  retroactively given creation events by `init-db`.
- Output routes redirect with an explanation when a report has no remaining pets.
- Report notes are stored after whitespace trimming without a length cap. Only the
  flyer excerpt is limited to at most 200 characters, including an ellipsis.
  Other output/detail pages keep the full notes.

## 4. Cross-cutting requirements and verification

| ID | Requirement | Verification |
|---|---|---|
| NFR-S2-01 | Require login for owned application pages; filter records by authenticated owner; reject foreign report/contact IDs independently; ignore forged owner IDs. | Separate-session list/GET/POST checks; foreign records return 404 |
| NFR-S2-02 | Retain CSRF protection on modifying form submissions, server-side validation, and escaped templates; keep generated-output requests read-only. | Valid/invalid/missing/cross-session token checks, inline-error/no-write tests, escaping and method checks |
| NFR-S2-03 | Preserve prior users/pets/contacts/reports, routes, templates, styles, and behavior when adding schema/features or resolving conflicts. | Additive database checks, diff review, and relevant combined-code regressions |

This is scoped verification, not an exhaustive security certification. Private
media delivery is not established: uploaded photos retain existing static URLs.

Performance/load, availability, compliance, retention, accessibility targets,
production security settings, and recovery objectives remain _TBD_ pending explicit
requirements. Example targets from the original scaffold are not treated as approved.

## 5. Interfaces and data

The [architecture document](../2-elaboration/architecture-design.md) defines route
methods, the six tables, owner relationships, and timestamp rules. The
[user manual](../4-transition/user-manual.md) describes the screens.

Email and phone use a contact picker. Social/flyer do not require a contact.
Generated content is not persisted or automatically sent/published. Browser-native
clipboard, photo download, mail-client, and print interfaces are used; there is no
external agency API or scheduled reminder service in the delivered feature set.

## 6. Acceptance and traceability

Implementation review passed for the recorded cases. Formal sponsor acceptance,
production deployment approval, and the definition of any additional requirement
remain _TBD_. The [test plan](../3-construction/test-plan.md) states evidence limits.

| Requirement | Design element | Test case |
|---|---|---|
| FR-S2-01 | Contact model / contacts blueprint | TC-S2-01 |
| FR-S2-02 | Report / ReportPet models and ORM relationships | TC-S2-02 |
| FR-S2-03 | Reports blueprint / form timezone script | TC-S2-03, TC-S2-04 |
| FR-S2-04 | ReportStatusEvent / status route | TC-S2-05 |
| FR-S2-05 | Agency-email builder / shared picker | TC-S2-06 |
| FR-S2-06 | Phone-script builder / shared picker | TC-S2-07 |
| FR-S2-07 | Social builder / photo links | TC-S2-08 |
| FR-S2-08 | Flyer route / excerpt helper / print CSS | TC-S2-09 |
| FR-S2-09 | Login stale-pet helper | TC-S2-10 |
| NFR-S2-01, NFR-S2-02 | Owner filters / Flask-Login / Flask-WTF / Jinja | TC-S2-11 |
| NFR-S2-03 | Additive schema and integration policy | TC-S2-12 |

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | Codex | Replace placeholder requirements with the delivered Sprint 2 baseline and traceability; retain unapproved scope as pending. |
