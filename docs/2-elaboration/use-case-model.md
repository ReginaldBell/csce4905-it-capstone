# Use Case Model

**Phase:** Elaboration | **Status:** Sprint 2 implementation documented; acceptance _TBD_

**Owner:** _TBD_ | **Baseline:** `4d51cc3`, November 4, 2026

## 1. Actors and scope

| Actor | Role |
|---|---|
| Pet owner | Authenticated primary user of owned pets, contacts, reports, and outputs |
| Visitor | Registers or logs in before accessing owned records |
| Browser / configured mail client | Copies text, downloads photos, opens email drafts, or prints a flyer when requested |

An agency contact is stored data, not an authenticated actor. The application does
not contact agencies or publish content automatically. Sponsor-specific actors
and a formal use-case diagram remain _TBD_.

See [requirements](../1-inception/requirements-srs.md) and the
[Sprint 2 decisions](../project-management/sprint-2-record.md).

## 2. Use case index

| ID | Name | Requirement |
|---|---|---|
| UC-S2-01 | Maintain contacts | FR-S2-01 |
| UC-S2-02 | File and view a missing-pet report | FR-S2-02, FR-S2-03 |
| UC-S2-03 | Update report status and view history | FR-S2-04 |
| UC-S2-04 | Prepare an agency email | FR-S2-05 |
| UC-S2-05 | Prepare a phone script | FR-S2-06 |
| UC-S2-06 | Prepare a social post and photos | FR-S2-07 |
| UC-S2-07 | Print a flyer | FR-S2-08 |
| UC-S2-08 | Review stale pet information after login | FR-S2-09 |

All owner workflows inherit NFR-S2-01 through NFR-S2-03. Existing account and pet
CRUD workflows remain in place; the [user manual](../4-transition/user-manual.md)
covers them alongside the Sprint 2 additions.

## 3. Use case specifications

### UC-S2-01 — Maintain contacts

**Actor:** owner. **Precondition:** signed in. **Trigger:** opens Contacts.
**Postcondition:** valid changes are stored only under that owner.

1. View contacts grouped by category and ordered by name.
2. Add a contact with category/name and phone, email, or both; notes are optional.
3. Open its detail page and edit as needed.
4. For deletion, open confirmation and submit the deletion form.

**Alternates:** custom categories are allowed. Invalid/oversized fields and absent
contact methods produce inline errors with submitted values retained. An email-only
or phone-only contact is valid. Foreign/missing contacts return 404; forged owner IDs
are ignored; missing/invalid CSRF prevents modification.

### UC-S2-02 — File and view a missing-pet report

**Actor:** owner. **Precondition:** signed in, with at least one saved pet.
**Trigger:** chooses File a report. **Postcondition:** an open owned report links the
selected owned pets; current code also creates its initial status event.

1. Select one or more pets.
2. Supply a last-seen location and optionally a local date/time and notes.
3. The browser supplies the selected date's UTC offset, including DST.
4. The server validates, converts time to UTC, and saves the report and links.
5. View pets, location, UTC-labelled sighting time, full notes, status/history, and outputs.

**Alternates:** no pets redirects to Add a pet on GET or POST. No owned selection,
blank/oversized location, malformed/future time, or out-of-range offset produces
inline errors without a new report. Mixed forged/owned pet IDs retain only the
owned IDs. Missing/non-numeric offset follows the zero-offset fallback; a blank
time remains unknown. Other users' reports do not appear in lists and return 404.

Deleting a linked pet later removes that link, not the report. A report with no
pets remains viewable, but output generation follows the empty-pets alternate below.

### UC-S2-03 — Update report status and view history

**Actor:** owner. **Precondition:** owns a report. **Trigger:** submits a new status.
**Postcondition:** an actual change and its event are committed together.

1. Choose Open, Found, or Closed on report detail.
2. Submit the CSRF-protected form.
3. The server records the old/new status and UTC event time.
4. Read the oldest-first history, including filing for reports created with history enabled.

**Alternates:** entering Closed sets `closed_at`; leaving it clears that value.
Submitting the same status shows information without changing timestamps/history.
An invalid status changes nothing. Another user's valid-session submission still
returns 404. Schema initialization does not backfill events for pre-existing reports.

### Shared output alternate

Email, phone, social, and flyer require an owned report with at least one remaining
pet. If all linked pets were deleted, the system redirects to report detail with
an explanatory error. It keeps the report/history and does not generate an empty
output. Missing/foreign reports return 404; anonymous visitors go to login.

Outputs are built from current data on each request. They are not saved output
versions, and changes do not update already copied/printed/sent material.

### UC-S2-04 — Prepare an agency email

**Actor:** owner. **Precondition:** owned report with pets and an owned contact.
**Trigger:** chooses Email an agency. **Postcondition:** subject/body are available
for copying or opening in the user's email application.

1. Choose a contact from the shared picker.
2. Review generated pet descriptions, last-seen data, full notes, and reporter email.
3. Copy subject/body or open the encoded mailto draft and send outside Pet Finder.

**Alternates:** no contacts offers Add one. A contact without email suppresses the
mailto action but allows copying. Report and contact IDs are checked independently;
own report plus foreign contact and foreign report plus own contact return 404.

### UC-S2-05 — Prepare a phone script

**Actor:** owner. **Precondition:** owned report with pets and owned contact.
**Trigger:** chooses Generate phone script. **Postcondition:** a script is displayed.

1. Select the contact through the shared picker.
2. Review the script, including full report notes and reporter email.
3. Read or copy it, then place the call outside Pet Finder.

**Alternates:** no contacts offers Add one; absent phone number shows a fallback
instead of blocking the script. Independent report/contact ownership checks and
the shared empty-pets alternate apply.

### UC-S2-06 — Prepare a social post and photos

**Actor:** owner. **Precondition:** owned report with pets; no contact needed.
**Trigger:** chooses Generate social post. **Postcondition:** caption/photos are
available for manual posting elsewhere.

1. Review caption, pet descriptions, last-seen data, full notes, email, and hashtags.
2. Copy the caption and download available pet photos.
3. Publish in the chosen external social application.

**Alternates:** pets without photos are named in a fallback note. A missing
physical file retains the existing static-file 404 behavior. The route is owned,
but inherited static photo URLs are directly accessible.

### UC-S2-07 — Print a flyer

**Actor:** owner. **Precondition:** owned report with pets; no contact needed.
**Trigger:** chooses Printable flyer. **Postcondition:** browser print output is prepared.

1. Review all names, deduplicated species, last-seen data, and reporter email.
2. Use the first linked pet with a photo as the cover, if any.
3. Display at most 200 note characters, with an ellipsis for a longer note.
4. Choose Print this flyer; the browser hides navigation, flashes, and Print/Back controls.

**Alternates:** no photos omits the image block. Full notes remain unchanged in the
database and other views. The long-notes/photo regression printed one page in
Chrome; the user checks preview for their paper/printer settings. The shared
empty-pets alternate applies.

### UC-S2-08 — Review stale pet information after login

**Actor:** owner. **Precondition:** supplies valid login credentials.
**Trigger:** successful login. **Postcondition:** login succeeds; any stale pets are
named in one informational reminder.

1. Authenticate normally.
2. Query only that owner's pets with updated_at strictly before UTC now minus 90 days.
3. If any match, show their names alphabetically and ask the owner to review profiles/photos.
4. The owner visits My Pets and edits information when needed.

**Alternates:** exactly 90 days, fresh/no-pet users, failed login, and registration
produce no stale reminder. There is no background message, automatic edit, or
separate acknowledgement action.

## 4. Verification and pending modelling

[TC-S2-01 through TC-S2-12](../3-construction/test-plan.md) cover these workflows
and relevant regressions. Formal sponsor validation, additional diagrams, and
requirements outside this recorded increment remain _TBD_.

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | Codex | Document eight implemented Sprint 2 use cases, alternate flows, ownership, and output limits. |
