# Sprint 2 Delivery and Decision Record

**Recorded:** November 4, 2026

**Application baseline:** [`4d51cc3`](https://github.com/ReginaldBell/csce4905-it-capstone/commit/4d51cc3848699165b77513cad5ea797fc35f97e7)

**Scope:** delivered implementation cards 3–11, PRs #12–#20.

This is the historical record of Sprint 2 changes, implementation decisions,
review defects, and merge outcomes. [PROJECT_STATE.md](../../PROJECT_STATE.md)
is the living status and next-action index. Card numbers identify plan items;
they are not GitHub PR numbers. No disposition for other plan cards is invented.

## Delivery ledger

All nine PRs below were reviewed, merged with merge commits, and had their source
branches deleted. The order shown is the actual main-branch integration order.

| Card | Deliverable | PR | Merge commit | Source branch |
|---|---|---|---|---|
| 4 | Report / ReportPet models only | [#12](https://github.com/ReginaldBell/csce4905-it-capstone/pull/12) | `4ea6b5e` | `feature/4-reports-tables` |
| 3 | Contact model/table and CRUD | [#13](https://github.com/ReginaldBell/csce4905-it-capstone/pull/13) | `1a5e280` | `feature/3-contacts-crud` |
| 5 | Report Missing form/list/detail | [#14](https://github.com/ReginaldBell/csce4905-it-capstone/pull/14) | `801821a` | `feature/5-report-missing-form` |
| 11 | Report status and history | [#15](https://github.com/ReginaldBell/csce4905-it-capstone/pull/15) | `4f7cea4` | `feature/11-report-status-history` |
| 6 | Agency email generator | [#16](https://github.com/ReginaldBell/csce4905-it-capstone/pull/16) | `a429109` | `feature/6-agency-email-generator` |
| 10 | Stale-pet reminder at login | [#20](https://github.com/ReginaldBell/csce4905-it-capstone/pull/20) | `a6e6783` | `feature/10-stale-pet-reminder` |
| 7 | Phone script generator | [#17](https://github.com/ReginaldBell/csce4905-it-capstone/pull/17) | `18acacb` | `feature/7-phone-script-generator` |
| 8 | Social post and photo downloads | [#18](https://github.com/ReginaldBell/csce4905-it-capstone/pull/18) | `f2615b1` | `feature/8-social-post-generator` |
| 9 | Printable flyer and print stylesheet | [#19](https://github.com/ReginaldBell/csce4905-it-capstone/pull/19) | `4d51cc3` | `feature/9-printable-flyer` |

## Delivered changes

| Area | Final behavior |
|---|---|
| Contacts | Category/name required, at least phone or email required; optional notes; category grouping and alphabetical names; owner-scoped CRUD with delete confirmation. |
| Report schema | `reports` and `report_pets` link one report to multiple pets. Existing users/pets retained; no report routes/templates in the schema-only PR. |
| Report form | One or more owned pets, required location (255 max), optional last-seen time and notes; no-pets redirect; forged pet IDs cannot link another owner's pet. |
| Time handling | Date-specific browser offset, UTC normalization before future-time validation/storage, UTC label on report detail, bounded offset. |
| Status/history | All transitions among `open/found/closed`; creation and actual changes logged; closed_at set/cleared; same-status no-op. |
| Agency email | Subject/body, singular/plural wording, last-seen details, full notes, reporter email; individual copy controls and encoded mailto when contact has email. |
| Phone script | Contact picker, script with full notes, phone-on-file/fallback display, copy control; shared picker refactor preserves email. |
| Social output | Caption with pets, UTC time when supplied, full notes, reporter email, hashtags; available photos downloadable, missing photos named. |
| Flyer | First linked pet with photo, all names, deduplicated species, last-seen details, reporter email, notes excerpt; print hides navigation/flash/controls. |
| Reminder | Successful login checks only that owner's Pet.updated_at; strictly older than 90 days produces one sorted singular/plural informational message. |

## Decision log

### S2-D01 — Fold contacts schema into Contacts CRUD

The plan referred to an existing contacts table that did not exist. Card 3 therefore
delivered both `Contact`/`contacts` and the UI/routes in PR #13. This removed a false
dependency. PR #12 remained report schema only; #12 and #13 could merge independently.

### S2-D02 — Model a report as a multi-pet record

`ReportPet` is an explicit join model, and `Report.pets` exposes linked pets.
ORM `all, delete-orphan` cascades remove report-pet links when a pet is deleted,
but retain the report and its status history. Deleting a report removes its
join/history rows; deleting a user removes their owned records through ORM
relationships. These are ORM behaviors; raw SQL does not gain database
`ON DELETE CASCADE` clauses from them.

### S2-D03 — Scope every application lookup and write to the owner

Pet, contact, and report queries use the authenticated user's ID. Creation assigns
owner IDs on the server, ignoring forged form owner IDs. Report pet selection
filters to owned pets and deduplicates IDs; forged-only selections fail validation.
Email/phone output routes independently check both report and contact ownership.
Authenticated requests for missing or another user's records return 404;
anonymous protected-page requests go to login.

This application-route rule does not make uploaded media private: existing photos
are served through Flask static URLs, unchanged during Sprint 2.

### S2-D04 — Validate submitted fields on the server

Forms show inline errors instead of relying on browser attributes. Contacts require
category (max 50), name (max 100), and at least one contact method. Email is format
checked and at most 255 characters to match the PostgreSQL column. Phone accepts
7–30 formatting/digit characters and requires at least one digit; punctuation-only
values fail. This is syntactic validation, not verification that a phone or inbox exists.
Report location is required and at most 255 characters. Templates extend `base.html`;
Flask-WTF CSRF protection remains enabled for form submissions.

### S2-D05 — Normalize selected local sighting time to UTC

The datetime-local input has no timezone itself. Vanilla JavaScript computes
`new Date(lastSeenInput.value).getTimezoneOffset()` using the selected date,
updates on input/change, and recomputes before submit. The server adds those
minutes to the parsed local value, then compares/stores UTC using the existing
naive-UTC timestamp convention.

Offsets `-840` through `720` minutes are accepted inclusively; `-841`, `721`,
and absurd numeric values produce a last-seen field error without saving a report.
Missing/non-numeric offsets retain the implemented zero-offset fallback.
A blank time remains optional. Report detail labels the stored value UTC.
Automatic local conversion therefore requires functioning browser JavaScript.

### S2-D06 — Log actual status changes and handle closure explicitly

New reports start `open` and receive a history event with `from_status=None`.
Each real transition records old/new status and UTC time. History is displayed
oldest first. Any of the three valid statuses may transition to another; there
is no additional state-transition restriction. Entering `closed` sets `closed_at`;
leaving it clears the value. Same-status submissions add no event or timestamp
update. Invalid statuses do not alter the report. The table is a status log,
not a full audit log of every field edit or actor.

### S2-D07 — Generate outreach from current data on demand

Generated email, phone script, social caption, and flyer are not separate stored
records. GET routes render current report/pet data and the owner's account email.
The app does not send email, place calls, publish posts, or keep a sent-output
history. Copies already downloaded, printed, or sent do not change on regeneration.

### S2-D08 — Share contact selection only where needed

Email and phone script select an owned contact through generic
`outputs/pick_contact.html`. Social and flyer routes need no contact. A phone-only
contact suppresses email's mailto link but still permits copying text; an email-only
contact shows the phone-number fallback. The picker refactor retained email behavior.

### S2-D09 — Guard outputs when all linked pets have been deleted

A report legitimately survives the deletion of its last pet. All output entry
points check for remaining pets and redirect to report detail with an explanatory
flash when empty. The pet-list helper also handles an empty list safely.
The existing report-preserving pet cascade was retained rather than changed to
hide the email crash found in review.

### S2-D10 — Shorten only flyer notes

`MAX_FLYER_NOTES_LENGTH=200` limits the displayed flyer excerpt. Values over the
limit use up to 199 characters, trailing whitespace removed, plus an ellipsis;
shorter values are unchanged. `Report.notes` remains unbounded stored text after
normal form trimming, and full notes still render in report detail, email, phone,
and social output.

The actual 80-times-repeated sentence/photo repro changed from four PDF pages
(contact on page four) to one page (contact on page one) in headless Chrome.
This is evidence for that layout and fixture, not a guarantee for every number
of pets, printer, paper size, or arbitrary content.

### S2-D11 — Use browser capabilities for copying, downloads, mail, and print

Use vanilla `navigator.clipboard.writeText` handlers, normal photo download links,
URL-encoded `mailto:`, and `window.print()` with a print stylesheet. No JavaScript
framework, email service, or server-side PDF-generation dependency was added.
Print hides `.site-header`, `.flash-messages`, and `.no-print` controls. Browser
clipboard execution/permission failures were not fully exercised during review.

### S2-D12 — Remind at successful login, not through a scheduled service

After `login_user()`, query owned pets with `updated_at < utcnow - 90 days`.
Exactly 90 days is excluded; 90 days plus one microsecond is included in the
frozen-clock regression. One info flash names pets alphabetically with singular/
plural wording. Registration, failed login, and users without stale pets do not
get the message. There is no background job, outbound reminder, or acknowledgement
field.

### S2-D13 — Keep schema additions additive and protect prior data

`flask init-db` calls `db.create_all()` to create missing tables without dropping
existing users/pets/contacts/reports. It does not alter existing columns, backfill
old report history, or constitute a schema-migration framework. New schema changes
need an explicit migration plan. PostgreSQL's named volume and uploaded files
must both be retained for operational continuity.

### S2-D14 — Review independently, integrate dependencies, preserve both sides

PRs #12/#13 were independent. The requested integration sequence was #14, #15,
then #16; #15/#16 both needed #14's fix. Later PRs #17–#20 were independent of
each other beyond main. The flyer defect did not block phone, social, or reminder
merges.

Shared files still conflicted after independent branches landed. Resolutions kept
both additions in models, blueprint registration, navigation, CSS, output functions,
and report detail. Relevant combined-code regressions were repeated. All accepted
PRs used merge commits, followed by source-branch deletion; defective PRs stayed
open with comments until fixes were re-reviewed.

## Review defects and resolutions

| Defect | Evidence / consequence | Final correction |
|---|---|---|
| Contact email too long | A format-valid 262-character email raised PostgreSQL string truncation on create/edit | `88d2d3d` adds server max 255 plus input maxlength; inline errors verified |
| Punctuation-only phone | `-------` saved without usable contact information | `88d2d3d` requires a digit; normal phone/email still pass |
| Naive local time compared with UTC | Future Chicago time accepted; past Tokyo time rejected | `e9832bd` normalizes with supplied offset; propagated through `58b3acf` / `b6cb04a` |
| Today's offset used for another DST date | Oct 31 noon Chicago stored 18:00 rather than 17:00 UTC from a Nov 4 browser | `fdc7e9e` derives offset from selected date; propagated through `e97cf58` / `b3c3cd7` |
| Absurd numeric offset | Uncaught timedelta overflow and HTTP 500 | `fdc7e9e` bounds to `[-840,720]` before arithmetic; boundary/outlier no-write checks pass |
| Email preview after last pet deleted | Empty description list raised IndexError / HTTP 500 | `da0198d` adds route guard and helper safety; other outputs use same guard |
| Long flyer notes | 80 sentence repetitions plus photo printed four pages | `abb7419` shortens flyer notes only; `06862a0` reconciles with main; Chrome one-page repro and full-note checks pass |

These fixes were reviewed before final merges. Initial rejection comments are
historical findings, not unresolved defects on the accepted heads.

## Integration notes

- `260490e` preserved Contact plus Report/ReportPet model additions before PR #13 merged.
- `f8a2ce6` preserved status/history plus email output before PR #16 merged.
- `94250dc` preserved phone plus social output before PR #18 merged.
- `06862a0` retained phone/social/email plus flyer before PR #19 merged.
- The final PR #19 diff appends flyer behavior/styles/template and one report link;
  existing output code and CSS from main were retained verbatim.

## Validation and evidence limits

The [test plan](../3-construction/test-plan.md) records reproducible cases and
historical results. Earlier reviews used disposable PostgreSQL 16; later route
reviews used isolated SQLite/Flask snapshots. Actual rendered scripts were exercised
for selected-date timezone offsets, and headless Chrome produced before/after flyer
PDFs. Ownership tests used separate users and valid CSRF tokens so a 404 could be
distinguished from CSRF rejection.

Temporary harnesses/PDFs are not committed test automation. No CI, performance/load,
production deployment, browser-matrix certification, or sponsor sign-off is implied.
This documentation update records prior evidence; it does not claim to rerun the
application tests.

## Follow-up state

Use [PROJECT_STATE.md](../../PROJECT_STATE.md#pending-work-and-verification-limits)
for active follow-up work. Production ownership, sponsor acceptance, retained
test automation, browser coverage, and media/retention policies remain explicit
rather than being inferred from merged code.

## Revision history

| Date | Author | Summary |
|---|---|---|
| 2026-11-04 | Codex | Record Sprint 2 delivery, decisions, dependencies, review fixes, merges, and evidence limits. |
