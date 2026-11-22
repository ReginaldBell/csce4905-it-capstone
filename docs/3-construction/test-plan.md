# Test Plan

**Phase:** Construction | **Status:** Sprint 2 review results recorded; Sprint 3 official run recorded: 22 Pass, 5 Not run | **Owner:** _TBD_

## 1. Scope and evidence

This plan records regression procedures and historical review results for Sprint 2,
delivered through PRs [#12](https://github.com/ReginaldBell/csce4905-it-capstone/pull/12)
through [#20](https://github.com/ReginaldBell/csce4905-it-capstone/pull/20).
The completed sprint baseline is merge commit `4d51cc3` on `main`.

See the [SRS](../1-inception/requirements-srs.md),
[Use Case Model](../2-elaboration/use-case-model.md),
[Architecture & Design](../2-elaboration/architecture-design.md), and
[Sprint 2 record](../project-management/sprint-2-record.md) for requirements,
implementation decisions, fixes, and merge history.

Results summarize checks already performed during PR review and re-review.
Writing this document did not execute another test run. Temporary review
harnesses and rendered PDFs are not a committed automated test suite.

## 2. Strategy and environments

| Level | Sprint 2 coverage | Evidence |
|---|---|---|
| Source review | Full descriptions/diffs, fix deltas, reconciliation with main, preservation of earlier code | PR review threads and merge commits |
| Database integration | Additive tables, ORM relationships/cascades, column validation, persisted time/status/history | Disposable PostgreSQL 16 during PRs #12–#16 |
| Route integration | Form submissions, CSRF tokens, separate authenticated sessions, outputs and downloads | PostgreSQL/Flask for early PRs; isolated SQLite/Flask snapshots for #17–#20 and final flyer re-review |
| Browser script | Actual report-form JavaScript under Chicago timezone rules; initial, input/change, and submit behavior | Node execution of rendered script during timezone re-review |
| Print rendering | Actual flyer template/CSS, photo fixture, PDF page count/contact placement and hidden controls | Headless Chrome PDFs before and after flyer fix |
| Acceptance | Sponsor demonstration/sign-off | _TBD_; merge review is not sponsor acceptance |

Fixtures include separate owner/other-user accounts, an account with no pets,
owned/foreign pets and contacts, multi-pet reports, and photo/no-photo pets.
Time-sensitive checks freeze the comparison clock or set timestamps explicitly.
Historical databases/containers were disposable and separate from user data.

For future runs, use a fresh test database and temporary upload directory. Do not
backdate or delete real user data to reproduce these cases. See the
[maintenance setup](../4-transition/maintenance-manual.md). SQLite route checks
supplement PostgreSQL schema/constraint checks; they do not replace them.

## 3. Entry and exit criteria

**Entry:** identify the exact PR head/integrated tree, read its diff/description,
prepare test fixtures, retain CSRF enforcement for security cases, and establish
the already-merged baseline.

**Review exit:** stated behavior and relevant regressions pass; reproduced
blocking defects are fixed and re-reviewed; merges preserve earlier functionality.
Failing independent PRs stay unmerged while passing independent PRs can land.
Sprint 2 met this review exit at `4d51cc3`. Sponsor acceptance, performance targets,
and production-readiness approval remain outside this recorded result.

## 4. Case index and traceability

| Case | Requirement | Use case | Coverage |
|---|---|---|---|
| TC-S2-01 | FR-S2-01 | UC-S2-01 | Contact CRUD, grouping, validation |
| TC-S2-02 | FR-S2-02 | UC-S2-02 | Report tables, additive setup, relationships/cascades |
| TC-S2-03 | FR-S2-03 | UC-S2-02 | Report form, selected pets, required fields, empty state |
| TC-S2-04 | FR-S2-03 | UC-S2-02 | UTC, DST, offset bounds and future-time validation |
| TC-S2-05 | FR-S2-04 | UC-S2-03 | Status/history, closed_at, same-status no-op |
| TC-S2-06 | FR-S2-05 | UC-S2-04 | Agency email, picker, mailto and empty-pets guard |
| TC-S2-07 | FR-S2-06 | UC-S2-05 | Phone script and shared picker |
| TC-S2-08 | FR-S2-07 | UC-S2-06 | Social caption, photo download, no-photo fallback |
| TC-S2-09 | FR-S2-08 | UC-S2-07 | Flyer print rendering and flyer-only notes truncation |
| TC-S2-10 | FR-S2-09 | UC-S2-08 | Login reminder strictly older than 90 days |
| TC-S2-11 | NFR-S2-01, NFR-S2-02 | UC-S2-01 through UC-S2-08 as relevant | Owner isolation, forged IDs, CSRF, escaping, read-only output |
| TC-S2-12 | NFR-S2-03 | All Sprint 2 use cases | Earlier functionality preserved through integration |

These are required regression cases for subsequent changes to the same behavior.
Recorded passes are scoped to the checks below, not exhaustive security/browser testing.

## 5. Reproducible regression cases

### TC-S2-01 — Contacts

1. Create contacts in two categories with names entered out of order. List, view,
   edit, open deletion confirmation, POST deletion, and verify 404 afterward.
2. Submit blank category/name, malformed phone/email, and no phone or email.
3. On create and edit, submit `"a" * 250 + "@example.com"` (262 characters), and
   submit `phone=-------` with no email. Check 255/256-character email boundaries.
4. Submit normal phone-only/email-only contacts and a forged `owner_id`.

Expected: category grouping and alphabetical names; inline errors without writes
or HTTP 500; punctuation-only phones rejected; accepted-format email at 255 saves
and 256 is rejected; legitimate data saves under the authenticated owner.
See [PR #13](https://github.com/ReginaldBell/csce4905-it-capstone/pull/13).

### TC-S2-02 — Report data and cascades

Seed users/pets, run `flask init-db` on the test database, and confirm existing
rows survive while new report/link tables, indexes and foreign keys exist.
Link two pets to a report and verify `report.owner`/`report.pets`. Delete one pet
through the ORM: its link disappears while the report/other link survive.
Delete a report: its links disappear while pets survive. Delete an owner through
the ORM: their related data disappears while another owner's data survives;
include contacts/status events after those models are installed.

Expected: additive setup and the documented SQLAlchemy ORM cascades. This does
not assert equivalent raw-SQL `ON DELETE CASCADE` behavior.
See [PR #12](https://github.com/ReginaldBell/csce4905-it-capstone/pull/12).

### TC-S2-03 — Report form

With no pets, GET/POST `/reports/new` must redirect to add a pet. With two owned
pets, select both and file a report with a location, leaving optional time empty.
Check whitespace/blank location, location over 255 characters, invalid time, and
no selection. Submit foreign-only/nonexistent IDs, mixed owned/foreign IDs,
duplicate IDs, and forged `owner_id`/creation status.

Expected: a valid report starts open, belongs to the authenticated user, and links
only their selected pets. Foreign-only selection is rejected; mixed selection
keeps only owned pets and duplicates create no duplicate link. Invalid forms
render inline errors without persisting a report. Listing/detail are owner-scoped.
See [PR #14](https://github.com/ReginaldBell/csce4905-it-capstone/pull/14).

### TC-S2-04 — UTC, DST, and offset bounds

Freeze comparison time at **2026-11-04 18:00 UTC**:

| Submitted local time | tz_offset_minutes | Expected |
|---|---:|---|
| Chicago, November 4 13:00 | 360 | Future error, no write |
| Chicago, November 4 11:30 | 360 | Store November 4 17:30 UTC |
| UTC+9, November 5 02:50 | -540 | Store November 4 17:50 UTC |
| UTC+9, November 5 03:05 | -540 | Future error, no write |

Execute the actual form script in America/Chicago with page-load date November 4.
Select **October 31, 2026 12:00 local**: offset must be **300**, storing **17:00 UTC**
instead of 18:00. Change to November 4 and verify 360. Exercise initial value,
`input`, `change`, and submit so the offset follows the selected date.

Using a past date, offsets **-840 and +720** must convert/save. Values **-841,
+721, -10000000000, +10000000000**, and a much larger integer must return the
inline date/time error without persisting anything. Empty/non-numeric offsets
retain the implemented zero fallback; empty optional time remains accepted.
Report detail labels the stored last-seen time UTC.

See [PR #14](https://github.com/ReginaldBell/csce4905-it-capstone/pull/14) and
propagation into [#15](https://github.com/ReginaldBell/csce4905-it-capstone/pull/15)
and [#16](https://github.com/ReginaldBell/csce4905-it-capstone/pull/16).

### TC-S2-05 — Status and history

File a report after history is installed; verify initial `None → open`. Submit
`open → found → closed → open`, then `open → closed → found`. Verify one ordered
event per real transition with correct old/new status, closed_at set on entering
closed and cleared on leaving it. Submit the current status and an invalid value.

Expected: same-status submits preserve history count, closed_at and updated_at;
invalid status changes no data. Another user's valid-session CSRF token does not
authorize the change: the route returns 404.
See [PR #15](https://github.com/ReginaldBell/csce4905-it-capstone/pull/15).

### TC-S2-06 — Agency email

Use single/multi-pet reports and an owned contact. Verify subject/body, grammar,
pet descriptions, last-seen data, notes and reporter email. Decode mailto recipient,
subject and body and compare with rendered values, including special characters.
Use a phone-only contact: no-email note and no mailto link. With no contacts,
verify the add-contact link. Delete the report's last pet, then open picker/preview.

Expected: empty-pet routes redirect (302) to the report, followed by 200 and a
clear error; the report survives pet deletion. The pet-list helper also handles
an empty list without IndexError. Foreign report + owned contact and owned report
+ foreign contact independently return 404.
See [PR #16](https://github.com/ReginaldBell/csce4905-it-capstone/pull/16).

### TC-S2-07 — Phone script and shared picker

Verify single/multi-pet wording, last-seen UTC time, notes, reporter email and
selected contact. Test phone/no-phone contacts, owner-only sorted options,
no-contact fallback, missing IDs, empty-pets routes and both independent ownership
checks. Repeat email selection after the generic-picker refactor. With valid CSRF,
POST to a GET-only generated-output endpoint returns 405.
See [PR #17](https://github.com/ReginaldBell/csce4905-it-capstone/pull/17).

### TC-S2-08 — Social post and photos

Verify singular/plural text, UTC time, notes, reporter contact, hashtags and escaping.
Use mixed photo/no-photo pets. Download the actual image and check bytes/MIME plus
the link's download attribute; the no-photo note names the other pet. Check
cross-user 404, anonymous redirect, read-only POST rejection and empty-pets guard.

Static photo URLs were already public before Sprint 2; this does not establish
private media storage. Missing physical files retain the static-file 404 behavior.
See [PR #18](https://github.com/ReginaldBell/csce4905-it-capstone/pull/18).

### TC-S2-09 — Flyer, notes scope, and print repro

Use a report whose first pet lacks a photo and a later pet has one. Verify first
available photo, all names, deduplicated species, last-seen data, reporter contact,
no-photo fallback, cross-user 404 and empty-pets redirect.

Use the following exact notes with a photo:

```python
notes = (
    "A brown and white dog wearing a blue collar was last seen near the park. "
    * 80
).strip()
# 5,839 stored characters
```

Render the actual template/CSS to PDF in headless Chrome. Verify **one page with
contact information on page one**; repeat a short-notes fixture. Navigation, an
injected flash probe, and Print/Back controls must be absent from the PDF.

The flyer shows at most 200 note characters, with an ellipsis when truncated.
Check helper boundaries 199/200/201 and None. On the same report, verify all
5,839 characters/all 80 repetitions on report detail, email, phone script and
social post. Database notes, updated_at and history must remain unchanged by GETs.

Before the fix, the long fixture printed **four pages**, contact on page four.
After `abb7419`, reconciled in `06862a0`, it printed **one page**, contact on page
one. The short fixture also printed one page. This validates the tested fixtures
and browser settings, not arbitrary pet counts, names, paper sizes or scaling;
check print preview for the intended output.
See [PR #19](https://github.com/ReginaldBell/csce4905-it-capstone/pull/19).

### TC-S2-10 — Stale-pet reminder at login

Freeze time. Seed owned pets updated 89 days ago, exactly 90 days ago, 90 days plus
one microsecond ago, and 91 days ago; also seed an older foreign pet. Log in:

- 89/exactly 90 days are excluded; anything strictly older is included.
- One info flash names stale pets alphabetically, with correct singular/plural grammar.
- Foreign pets never appear; forged owner_id does not select a different user.
- Fresh/no-pets users receive no reminder; updating a pet removes it from the next reminder.
- Failed login and registration do not emit the reminder. Login/logout CSRF,
  normal next redirect and access to pets/contacts/reports still work.

See [PR #20](https://github.com/ReginaldBell/csce4905-it-capstone/pull/20).

### TC-S2-11 — Authorization, CSRF, and escaping

Repeat other-user GET/POST requests using a genuinely valid CSRF token from that
other session; expect 404 rather than a request that merely failed CSRF first.
Verify foreign list entries are absent and owner_id forgery is ignored.
Independently vary report/contact IDs for email and phone routes.

For modifying forms, missing, invalid and other-session CSRF tokens must yield
400 without changes. Outputs stay GET-only and do not write records. Verify
untrusted names/notes are escaped. This is scoped application validation, not
an exhaustive penetration test.

### TC-S2-12 — Earlier functionality and integration

After reconciling branches, review diffs and exercise login and pet/contact CRUD,
report creation/validation, status/history and email output. Confirm History and
all merged output links remain, picker targets are correct, and prior CSS and
blueprint registrations remain. The final flyer reconciliation preserved existing
outputs.py/CSS content and added only the flyer link to report detail.

## 6. Defects found and resolved

| Defect | Repro | Fix / review outcome |
|---|---|---|
| Contact email overflow; punctuation-only phone saved | TC-S2-01 | `88d2d3d`: server email limit and digit requirement; #13 re-review passed |
| Local time compared directly with UTC | TC-S2-04 Chicago/UTC+9 cases | `e9832bd`: offset normalization, propagated upstream |
| Today's offset misconverted DST dates; absurd offset overflowed | TC-S2-04 DST/outlier cases | `fdc7e9e`: selected-date offset and bounds; propagated in `e97cf58` / `b3c3cd7` |
| Email crashed after report's last pet deletion | TC-S2-06 | `da0198d`: shared empty-pets guard and safe helper |
| Long notes/photo produced four-page flyer | TC-S2-09 | `abb7419`: flyer-only limit; `06862a0`: integration; actual PDF re-review passed |

Findings were recorded on affected PRs; those PRs stayed unmerged until re-review
passed. Independent #17/#18/#20 merged while #19's print defect was being fixed.

## 7. Historical results log

| Recorded date | PR / accepted baseline | Cases | Result and scope |
|---|---|---|---|
| 2026-11-04 | #12 / `4ea6b5e` | TC-S2-02, 12 | Passed PostgreSQL additive setup/relationships/cascades and login/pet checks |
| 2026-11-04 | #13 / `1a5e280` | TC-S2-01, 11, 12 | Passed PostgreSQL create/edit validation repros, isolation and CSRF after fixes |
| 2026-11-04 | #14 / `801821a` | TC-S2-03, 04, 11, 12 | Passed final DST/bounds re-review, actual form script and PostgreSQL persistence |
| 2026-11-04 | #15 / `4f7cea4` | TC-S2-04, 05, 11, 12 | Passed propagated fix and PostgreSQL status/history checks |
| 2026-11-04 | #16 / `a429109` | TC-S2-04, 05, 06, 11, 12 | Passed integrated PostgreSQL email/status/empty-pets/ownership checks |
| 2026-11-04 | #17 / `18acacb` | TC-S2-07, 11, 12 | Passed SQLite/Flask phone/email checks and combined-tree recheck |
| 2026-11-04 | #18 / `f2615b1` | TC-S2-08, 11, 12 | Passed SQLite/Flask text/download/isolation checks and combined-tree recheck |
| 2026-11-04 | #20 / `a6e6783` | TC-S2-10, 11, 12 | Passed SQLite/Flask exact-cutoff, login and CSRF checks |
| 2026-11-04 | #19 / `4d51cc3` | TC-S2-09, 11, 12 | Final SQLite/Flask and Chrome PDFs passed; full notes retained outside flyer |
| 2026-11-21 | Uncommitted `feature/material3-ui` | `tests/` suite; UI smoke checks | 26 unit tests passed. Disposable PostgreSQL upgrade from `4d51cc3` kept records. Chrome checked photos, map, settings persistence, 412/768 px layouts, and a one-page flyer |
| 2026-11-21 | Uncommitted `feature/material3-ui`, local `infra_pgdata` | Upgrade and read-only page checks | Dump created first; record counts matched after `init-db` and `upgrade-community`; signed-in list, form, pet, report, and Settings pages returned 200 |
| 2026-11-21 | Uncommitted `feature/material3-ui`, local app | Project-owner manual test | Owner reported everything working; individual cases were not itemized |
| 2026-11-21 | Uncommitted `feature/material3-ui`, isolated `petfinder-qa_pgdata` | Schema initialization and demo sign-in | `flask upgrade-community` completed on the QA volume. Verified 12 demo users, 25 pets, 24 reports, and 8 comments. Demo sign-in reached `/pets`. |
| 2026-11-21 | `sprint3/integration` at `1724829` | Automated suite | 180 test methods and 413 subtests passed, with no failures, errors, or skips. No formal TC outcome changed |
| 2026-11-21 | `sprint3/integration` at `1724829` | Photo authorization probe | On a real server with raw paths, 27 URL forms returned no private photo bytes to guests or unauthorized users. TC-107 remains Not run |
| 2026-11-22 | `sprint3/integration` at `1724829`, isolated `petfinder-qa` | Upgrade and smoke check | Backup taken; `init-db`, `upgrade-community`, and `upgrade-sprint3` ran with record counts unchanged. Demo sign-in and main pages returned 200 |
| 2026-11-22 | `1724829` plus heading-wrap patch | Official Sprint 3 run | 180 automated tests passed. 22 cases Pass and 5 Not run. See section 9 |
| 2026-11-22 | `1724829` plus heading-wrap patch | Project-owner browser report | Owner reported that a team member's Chrome and Firefox run was good. Browser versions and page details were not provided. TC-604 stays Not run until Safari is tested |
| 2026-11-22 | `sprint3/integration` at `1724829`, isolated `petfinder-qa` | Project-owner accessibility check | Owner reported a manual accessibility check. Individual cases, browsers, and results were not itemized, so TC-604 and TC-607 remain Not run |

Rows summarize coverage, not assertion counts or a claim that every case was
re-run on every merge commit. Reviews used relevant PR heads/reconciled trees
before merging; PR threads retain findings and re-review context.

## 8. Validation limits and remaining work

- No committed automated regression suite or CI execution was established by the
  Sprint 2 review work. `sprint3/integration` has 180 automated tests, but they are not
  merged and do not cover the manual browser and keyboard cases.
- Copy handlers were inspected; browser clipboard permission/interaction was not
  exercised. External mail-client behavior and actual delivery were not tested;
  this app generates text/mailto links and does not send mail.
- PDF checks cover the stated fixtures/settings. Cross-browser printing,
  accessibility, mobile usability, performance/load, restore testing and production
  deployment validation remain _TBD_.
- Sponsor acceptance and formal non-functional targets remain _TBD_. Reviewed
  merges do not establish acceptance of untested requirements or arbitrary layouts.

## 9. Sprint 3 test cases

The Sprint 3 work is implemented on `sprint3/integration`, not merged. The 27
cases below use the IDs in the course `TestPlanTracker.xlsx`, which holds their full
preconditions, steps, and expected outcomes. Change an outcome only after that exact
procedure runs, and record the commit and evidence.

| Case | Requirement | Test | Sprint 3 outcome |
|---|---|---|---|
| TC-001 | R1 | Register a household | Pass |
| TC-002 | R1, NF5 | Reject invalid account entries, including a used email | Pass |
| TC-003 | R1, NF2 | Log out and check private pages | Pass |
| TC-004 | R17, NF5, NF10 | Edit account details; outputs use saved phone | Pass |
| TC-005 | R23 | Reset a forgotten password | Pass |
| TC-101 | R2 | Add and save a pet with all identifiers | Pass |
| TC-102 | R2, NF5 | Require pet name and species | Pass |
| TC-103 | R3, NF2 | View pets and details | Pass |
| TC-104 | NF2 | Block another household's pets | Pass |
| TC-105 | R4 | Edit pet details | Pass |
| TC-106 | R5 | Confirm pet deletion | Pass |
| TC-107 | NF2, R20 | Keep photo links private | Pass |
| TC-108 | R2, NF5 | Reject a future birth date | Pass |
| TC-301 | R8, R9 | Add and view contacts, including address | Pass |
| TC-302 | R9, NF5 | Edit and delete contacts | Pass |
| TC-303 | NF2 | Keep contacts private | Pass |
| TC-604 | NF8 | Check supported screens and browsers | Not run |
| TC-605 | NF5 | Check form errors throughout the app | Not run |
| TC-607 | NF12 | Use a keyboard | Not run |
| TC-609 | NF14 | Limit repeated requests | Not run |
| TC-1001 | R1, NF1 | Password storage | Pass |
| TC-1002 | R1, NF2 | Session checks | Pass |
| TC-1003 | R2-R3, NF2 | Pet ownership | Pass |
| TC-1004 | R2, NF5 | Pet form checks | Pass |
| TC-1005 | R2-R3 | Saving and listing pets | Pass |
| TC-1006 | R2, NF5 | Special characters | Pass |
| TC-1014 | NF14 | Request limits | Not run |

### Official Sprint 3 run

Run on November 22, 2026 against `1724829` plus the heading-wrap CSS patch, using a real
Flask server, disposable PostgreSQL 16, Chrome 157.0.8103.79, and Edge 157.0.4341.46.
Reset mail used the local console backend.

**Result: 22 Pass, 0 open failures, 5 Not run.** The first run failed TC-604 because the
email and phone script pages scrolled sideways at 390 px with a long unbroken contact name.
Headings and hints now wrap. After the patch, all 42 page views per browser fit at 390 and
1280 px, and the flyer printed on one US Letter page in both browsers.

| Case | Passed so far | Still needed |
|---|---|---|
| TC-604 | Chrome and Edge at phone and desktop widths; Firefox reported passing by the project owner | Safari |
| TC-605 | Form errors on every available form | Report editing (R22) |
| TC-607 | Filing, error correction, Nearby, and opening a report by keyboard in Chrome | Sending a tip (R21) |
| TC-609 | Normal use and sign-in and reset limits | Report-filing and tip limits |
| TC-1014 | Sign-in limit, key hashing, expiry, and account separation | Report-filing and tip limits |

### Scope limits for this sprint

- **TC-607, TC-609, and TC-1014** include tip or report-filing behavior that is not in
  Sprint 3. Under the rule the project owner approved on November 21, 2026, automated tests
  and notes may record the Sprint 3 portion (sign-in and reset). The outcome stays
  **Not run** until the full written procedure is executed. Do not mark these cases Pass
  in Sprint 3.
- **TC-604** needs current Chrome, Edge, Firefox, and Safari. Record each browser
  separately.
- **TC-107** must be run as owner, another account, and guest, and with a replaced photo
  and a known old link. Also check that a non-owner can open a photo on a shared open
  report but not after that report is unshared, Found, or Closed. Repeat guest and
  unauthorized requests with `/static/./uploads/<file>`, `/static/x/../uploads/<file>`,
  `/static/%2e/uploads/<file>`, `/static/x/%2e%2e/uploads/<file>`, and backslash and
  repeated-slash forms; none may return photo bytes. Confirm other static assets still load.
  The November 22, 2026 official run recorded this procedure as Pass.
- **TC-605** treats the `pet_ids` checkbox group as one control. `aria-describedby` on its
  enclosing `fieldset` satisfies the field-error rule.

### How to run the automated suite

From your own checkout in Git Bash, with no network or database:

```bash
MSYS_NO_PATHCONV=1 docker run --rm --network none -v "$(pwd -W):/app" -w /app \
  -e PYTHONPATH=/app/src -e PYTHONDONTWRITEBYTECODE=1 infra-web \
  python -W ignore -m unittest discover -s tests
```

The command needs an existing `infra-web` image. Use synthetic data only: emails at
`@example.test` and phones in the `555-01xx` range. Any PostgreSQL check uses disposable
resources named `pfs3-*`, removed afterward. A passing unit test does not by itself mark
a manual or browser case as Pass. At commit `1724829`, the suite ran 180 test methods and 413 subtests with no failures, errors, or skips.

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | Codex | Recorded Sprint 2 regression procedures, traceability, historical evidence, resolved defects and validation limits through `4d51cc3` |
| 2026-11-21 | Claude | Recorded Material 3 UI, local database upgrade, and project-owner test evidence |
| 2026-11-21 | Claude | Add the Sprint 3 case list, scope limits, and suite instructions; all Sprint 3 outcomes remain Not run. |
| 2026-11-21 | Claude | Apply contract Addenda A and B: partial-case rule and shared photo checks, implemented on `sprint3/integration`, not merged. |
| 2026-11-21 | Claude | Apply integration corrections and contract Addenda C and D: photo path and fieldset checks, implemented on `sprint3/integration`, not merged. |
| 2026-11-22 | Claude | Replace pending Sprint 3 status with recorded automated, QA, and owner-check evidence. |
| 2026-11-22 | Claude | Record the official Sprint 3 run: 22 Pass and 5 Not run, with the 390 px heading overflow fixed. |
| 2026-11-22 | Claude | Record the project owner's Firefox report; TC-604 stays Not run until Safari is tested. |
