# Maintenance Manual

**Phase:** Transition | **Status:** Sprint 2 implementation documented; Sprint 3 operations merged to `main` through PRs #24 and #25; not deployed; production handover _TBD_

**Owner:** _TBD_ | **Audience:** maintainers | **Baseline:** Sprint 2 at `4d51cc3`, November 4, 2026; current `main` reviewed at `8038dc8`, including Sprint 3

## 1. System overview

Pet Finder is a Flask/Jinja application with SQLAlchemy/PostgreSQL persistence,
Flask-Login sessions, and Flask-WTF CSRF protection. Sprint 2 adds contacts,
missing-pet reports/history, generated outputs, and a login reminder while retaining
existing account/pet/photo behavior.

Use [architecture](../2-elaboration/architecture-design.md) for schema/routes,
[Sprint 2 decisions](../project-management/sprint-2-record.md) for rationale and fix
history, and [PROJECT_STATE.md](../../PROJECT_STATE.md) for pending operational work.

## 2. Environment and source layout

| Dependency | Repository version / role |
|---|---|
| Python container | `python:3.12-slim` |
| PostgreSQL container | `postgres:16-alpine` |
| Flask | 3.0.3 |
| Flask-SQLAlchemy | 3.1.1 |
| Flask-Login | 0.6.3 |
| Flask-WTF | 1.2.1 |
| psycopg2-binary | 2.9.9 |
| python-dotenv | 1.0.1 |
| black | 24.4.2; development formatter |

Versions come from `Dockerfile`, Compose, and `requirements.txt`, not an assessment
of latest package releases. Docker/Compose are required for the documented setup.

| Path | Responsibility |
|---|---|
| `src/app.py`, `src/extensions.py`, `src/config.py` | Factory, extensions, configuration, init-db command |
| `src/models.py` | Six tables: users, pets, contacts, reports, report_pets, report_status_events |
| `src/auth.py` | Account flows and login-only stale-pet reminder |
| `src/pets.py` | Pet CRUD and upload/file lifecycle |
| `src/contacts.py` | Contact CRUD, grouping, validation |
| `src/reports.py` | Report creation, timezone normalization, status/history |
| `src/outputs.py` | Email, phone, social, flyer; shared guards and contact picker |
| `src/templates/` | Jinja pages extending base.html |
| `src/settings.py` | Settings page and display-name updates |
| `src/static/css/app.css` | Shared screen styles and flyer print rules |
| `src/static/css/material.css` | Material 3 tokens, app shell, dark theme, and larger text |
| `src/static/js/preferences.js` | Browser-saved theme, text size, and default search radius |
| `src/static/uploads/` | Runtime photos, ignored by Git except .gitkeep |
| `infra/docker-compose.yml` | Local database/web services and persistence |

## 3. Build and run locally

From the repository root:

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml exec web flask init-db
docker compose -f infra/docker-compose.yml exec web flask upgrade-community
docker compose -f infra/docker-compose.yml ps
```

`flask upgrade-community` is required for a database created before the nearby feed.
It adds the missing columns, keeps existing records, and is safe to run again. Back up
any database holding data you need before running a schema change.

Open `http://localhost:5000/login` and register a test account. The application
has no `/` landing route. The web container starts Flask with `FLASK_APP=app.py`.
Compose waits for the database healthcheck before starting web. Web is exposed
on host port 5000; PostgreSQL is exposed on 5432.

To inspect logs or stop the development services without deleting the database:

```bash
docker compose -f infra/docker-compose.yml logs --tail=100 web db
docker compose -f infra/docker-compose.yml stop
```

Compose bind-mounts `src/` into the application container and enables development
reload. Rebuild/recreate after dependency, image, or environment changes:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

These commands were checked against the repository configuration while documenting;
this documentation task does not claim a new deployment/test run.

## 4. Schema and data operations

### Additive initialization

`flask init-db` runs `db.create_all()`. It creates missing tables without resetting
existing rows. Sprint 2 added `contacts`, `reports`, `report_pets`, and
`report_status_events` to the earlier `users`/`pets` schema.

The command does not alter existing columns, perform versioned migrations,
backfill creation-history events on old reports, or repair inconsistent data.
Plan and review a migration for future column/constraint changes. Do not replace
initialization with drop/create on a database containing user data.

### Relationships and deletion

- User relationships cascade ORM deletion to owned pets, contacts, and reports.
- Pet deletion removes ReportPet links; it preserves the report and its history.
- Report deletion removes its links/status events; it preserves Pet records.
- These are SQLAlchemy ORM cascades. The foreign keys do not declare raw-SQL
  ON DELETE CASCADE behavior; bulk SQL needs separate dependency handling.
- User/report deletion behavior is a model capability; this increment does not
  expose a new account-delete or report-delete UI.

All output routes handle reports whose last linked pet was deleted by redirecting
to the still-viewable report with an explanatory flash.

### Persistence and backups

The database lives in the Compose `pgdata` named volume. Photos live separately
on the host in `src/static/uploads/` through the source bind mount. Preserve both
when moving or recovering the application; copying the database alone does not
restore image files. Uploaded photos are not source-controlled.

Backup frequency, responsible owner, retention period, restore target, and tested
restore procedure are _TBD_. A future procedure should capture a PostgreSQL dump
and the matching upload files, then verify restoration in an isolated environment.
Do not claim a backup exists or is restorable without testing it.

To take a manual database dump before a schema change, run this from the repository
root while the services are up:

```bash
docker compose -f infra/docker-compose.yml exec db pg_dump -U petfinder -f /tmp/petfinder-backup.sql petfinder
docker compose -f infra/docker-compose.yml cp db:/tmp/petfinder-backup.sql ../petfinder-backup.sql
```

In Git Bash on Windows, run `export MSYS_NO_PATHCONV=1` first so `/tmp` is not
rewritten to a Windows path. Confirm the file ends with `PostgreSQL database dump
complete`. The dump holds account data, so keep it out of the repository. It does
not include uploaded photos, and restoring it has not been tested.

## 5. Configuration

| Setting | Source / delivered behavior |
|---|---|
| `DATABASE_URL` | Read by Config; defaults to the local PostgreSQL psycopg2 URL. Compose supplies its database service URL. |
| `SECRET_KEY` | Read by Config; development fallback exists. Production value/secret storage and rotation ownership are _TBD_. |
| `UPLOAD_FOLDER` | Defaults to src/static/uploads; keep within the served static tree for existing image URLs. |
| `MAX_CONTENT_LENGTH` | 5 MB, set in Config; caps uploaded requests/photos. |
| `ALLOWED_PHOTO_EXTENSIONS` / `ALLOWED_PHOTO_MIMETYPES` | JPG/JPEG/PNG and image/jpeg or image/png. |
| `FLASK_DEBUG` | Enabled by supplied local Compose configuration. |
| `FLASK_APP` / host | Container sets app.py and binds Flask to 0.0.0.0. |

Application constants such as the 90-day threshold, 200-character flyer excerpt,
and timezone bounds are code constants, not additional environment variables.

Production hosting, TLS termination, database exposure, deployment/rollback
procedure, logging/monitoring ownership, and account-access administration remain
_TBD_. The supplied debug/development settings are not a completed production design.

## 6. Behavior maintainers must preserve

### Validation and ownership

Contact category/name limits are 50/100; email format and max 255 are checked
before saving; phone syntax requires a digit and 7–30 allowed characters. At least
phone or email is required. Categories may be custom text.

Creation assigns owner IDs on the server; lookup/update/delete queries filter by
authenticated owner. Report selections deduplicate/filter owned Pet IDs.
Email/phone independently authorize the report and contact. Keep CSRF enabled when
testing other-user POSTs so a route 404 can be distinguished from a token error.

### UTC and history

Sighting time is optional. The form computes the selected date's browser offset
on input/change/submit, including DST. The server adds that offset to local time,
validates against UTC now, and stores naive UTC consistent with existing models.
Numeric offsets outside `[-840,720]` are inline errors; missing/non-numeric offsets
currently fall back to zero. A timezone identifier is not stored.

New reports get an initial None-to-open event. Actual status changes add an event;
same-status and invalid submissions do not alter status/history/timestamps.
Closing sets closed_at; leaving closed clears it. All valid statuses can
transition to one another. The history is not a general audit trail.

### Generated content and print

Email/phone/social/flyer are rebuilt from current saved data at GET time. They are
not saved output versions and the app does not send, call, or publish for the user.
The generic contact picker serves email/phone only. Browser-native copy, mailto,
download, and print behavior must remain compatible with the generated templates.

Only the flyer truncates notes, using MAX_FLYER_NOTES_LENGTH=200. Preserve
Report.notes and full rendering in detail/email/phone/social. The flyer chooses
the first linked pet with a photo path, deduplicates species, and uses print CSS
to hide navigation, flashes, and controls.

### Login reminder

After a successful login, only the owner's pets with updated_at strictly before
UTC now minus 90 days are named in one sorted informational flash. Exactly
90 days is excluded. Registration/failed login do not emit it. There is no
scheduler, reminder persistence, or acknowledgement flag.

## 7. Verification and troubleshooting

Use [TC-S2-01 through TC-S2-12](../3-construction/test-plan.md) for regression
procedures and recorded evidence. Historical checks used disposable PostgreSQL,
isolated SQLite/Flask snapshots, actual timezone scripts, and Chrome PDF output.
Temporary review harnesses are not a committed test suite or CI pipeline.

| Symptom | Check / action |
|---|---|
| Relation/table missing after upgrade | Verify database target and run additive init-db; investigate migrations if existing columns changed. |
| Login or pages fail with a missing-column error | Run `flask upgrade-community` against the intended database. |
| Photo URL 404 | Check stored photo_path and corresponding upload file; database restoration alone is insufficient. |
| Wrong report time | Check selected-date timezone script, offset sign/bounds, browser timezone, and zero-offset fallback. |
| Empty report output redirects | Expected after all linked pets were deleted; retain report/history and shared guard. |
| Email/phone picker links wrong | Confirm generic pick_contact.html receives the correct target endpoint. |
| Flyer spans extra pages | Re-run the actual PDF fixture and check print settings/content; break avoidance alone does not guarantee arbitrary layouts fit. |
| Stale reminder includes wrong pets | Check owner filter and strict updated_at cutoff using a frozen clock/test data. |
| POST fails before route ownership check | Supply a valid token from that test user's own session; use separate sessions for isolation cases. |

## 8. Known limits and handover work

- Since Sprint 3 merged to `main`, uploaded photo URLs are
  access-checked, and TC-107 passed on November 22, 2026.
- Clipboard handlers were inspected, but browser permission/failure cases and
  a formal browser support matrix were not fully tested.
- Missing/non-numeric timezone offset means UTC; automatic local conversion needs JS.
- Chrome verified the specific long-notes/photo flyer as one page, with contact on
  page one. Other paper sizes, printer settings, or arbitrary pet/content counts
  need preview/testing; no universal fit guarantee is recorded.
- Production operation, backup/restore validation, retention, performance targets,
  support ownership, and sponsor acceptance remain _TBD_.

Record follow-up decisions and changes in [PROJECT_STATE.md](../../PROJECT_STATE.md).
Never commit real credentials; document only their approved storage/access procedure
once one exists.

## 9. Sprint 3 upgrade and operations

This section applies to Sprint 3 work merged to `main` through PRs #24 and #25. It is not deployed. The upgrade ran on the
isolated `petfinder-qa` database on November 22, 2026 with record counts unchanged. It has
not run on `infra_pgdata` or any deployed database.

### Upgrade order

Back up first. There is no downgrade command, and restoring the dump has not been tested.

1. Confirm which database you are changing. Compose names the project `infra` from the
   folder name, so **every checkout uses the same `infra_pgdata` volume by default**. To
   try this version without touching it, stop the `infra` stack and add a separate project
   name such as `-p pfs3-trial` to each Compose command.
2. Take the database dump in [section 4](#persistence-and-backups) and confirm that it
   ends with `PostgreSQL database dump complete`.
3. Copy the photos, which are not in the dump:

   ```bash
   cp -r src/static/uploads ../petfinder-uploads-backup
   ```

4. Switch to the Sprint 3 code and rebuild:

   ```bash
   docker compose -f infra/docker-compose.yml up --build -d
   ```

5. Run the schema commands in this order:

   ```bash
   docker compose -f infra/docker-compose.yml exec web flask init-db
   docker compose -f infra/docker-compose.yml exec web flask upgrade-community
   docker compose -f infra/docker-compose.yml exec web flask upgrade-sprint3
   ```

6. Compare record counts for users, pets, contacts, and reports with the counts before
   the upgrade, then sign in and open the pet, contact, report, and Settings pages.

`flask upgrade-community` also adds `users.full_name`, `users.phone`, and
`users.session_version` (default 1), because existing code loads `User` after that command.
`flask upgrade-sprint3` is still required for all other Sprint 3 schema changes. Existing
sessions that hold only a user ID count as version 1.

Pages that read the new columns, including sign-in, can fail between steps 4 and 5, so
keep users off the app during the upgrade. Compose bind-mounts `src/` from the current checkout, so photos
saved under another checkout will not appear unless they are copied.

### Environment variables

| Setting | Default | Purpose |
|---|---|---|
| `APP_BASE_URL` | Blank | Base address for emailed reset links; required outside debug or testing |
| `MAIL_BACKEND` | `console` | `console`, `memory`, or `smtp` |
| `MAIL_HOST` | `localhost` | SMTP server |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | Blank | SMTP credentials; never commit them |
| `MAIL_FROM` | `no-reply@petfinder.example.test` | Sending address; the production provider and address are _TBD_ |
| `MAIL_USE_TLS` | `true` | SMTP TLS setting |
| `PASSWORD_RESET_TTL_MINUTES` | `60` | Reset link lifetime |
| `LOGIN_LIMIT`, `LOGIN_WINDOW_SECONDS` | `5`, `900` | Failed sign-in limit |
| `RESET_LIMIT`, `RESET_WINDOW_SECONDS` | `3`, `3600` | Reset request limit |

The approved Sprint 3 Compose change passes `APP_BASE_URL` and the
`MAIL_*` settings to the web service using `${NAME:-default}`, so no secret is written to
the file. Set real values in your shell or in an untracked `infra/.env` file.

The app also reads `PASSWORD_RESET_TTL_MINUTES`, `LOGIN_LIMIT`, `LOGIN_WINDOW_SECONDS`,
`RESET_LIMIT`, and `RESET_WINDOW_SECONDS` from its environment, but the supplied Compose
file does not forward them to `web`. Setting them in your shell or `infra/.env` has no
effect on that stack, so the defaults above apply. Forwarding them needs an approved
`infra/**` change.

### Operating notes

- The `console` backend prints only when `app.debug` or `app.testing` is true. The supplied
  Compose file sets `FLASK_DEBUG=1`, so full reset links can appear in its web logs. Treat
  those logs as sensitive, and do not use debug mode on a shared or public system.
- Outside debug or testing, `console` prints nothing, logs an error without message
  content, and counts as a failed send. Use `smtp` and set `APP_BASE_URL` there.
- If `APP_BASE_URL` is unset outside debug or testing, no reset email is sent.
- A successful password reset increments `session_version`, which logs out sessions
  started before the reset. It also clears login attempts for that email and client address.
- With the wrong backend or a failed send, users still see the generic success message.
  Check the web logs for a send failure.
- Limits use `request.remote_addr`. Behind a proxy or container gateway, many users can
  share one address. Review this before deployment.
- Retention and cleanup for `auth_attempts` and `password_reset_tokens` are _TBD_.

### Pending review patches

The behavior in this subsection applies only after patches P1-P11 are integrated and
verified. They are on `sprint3-fix/*` branches and are not recorded as passed, merged, or
deployed, so the known review bugs remain on `main` until they merge. See [PROJECT_STATE.md](../../PROJECT_STATE.md#sprint-3-review-patches).

| Patch | Operating change | What maintainers should do |
|---|---|---|
| P1, reset link | With `smtp` and no `APP_BASE_URL`, nothing is sent, even in debug. An error is logged without the token and the user sees the generic message | Set `APP_BASE_URL` wherever `smtp` is used |
| P2, verified TLS | With `MAIL_USE_TLS=true`, STARTTLS verifies the certificate and hostname | Set `MAIL_HOST` to a name on the certificate. A self-signed or private-CA relay fails unless the container trusts it |
| P3, sign-in limit | An attempt is reserved before the password check. Failures 1-5 show the normal error. The 6th attempt returns 429 even with the correct password. A correct password within the limit clears that key | Expect the same limit under concurrent requests |
| P4, reset limit | An accepted request is reserved before sending. A blocked retry sends nothing, shows the generic page, and does not extend the block | Wait for the window to pass; repeated retries do not lengthen it |
| P5, email change | A concurrent email conflict shows the inline email-taken error and rolls back | Treat a 500 on this path as a defect |
| P6, measurements | Very small saved values display in plain decimal form | Do not rewrite stored values |
| P7, comments | The author can delete a retained comment from `Your comments on unshared reports` on `/community`, then returns to the feed. Other requests get 404 | The section shows only that user's comment text, date, and Delete button. Unsharing still hides the post and comments from everyone else |
| P8, background SMTP | With `smtp`, reset mail sends from a daemon thread, so a slow server does not delay the response. `console` and `memory` stay synchronous | Check web logs for a send failure. Only the error type is logged. There is no retry, and a process stop can lose a message in progress |
| P9, registration email | Registration applies `MAX_EMAIL_LENGTH` and shows a field error | Treat a 500 on this path as a defect |
| P10, seed prerequisite | If Sprint 3 pet columns are missing, the seed prints the required commands and exits nonzero without a partial seed | Run `flask init-db`, `flask upgrade-community`, and `flask upgrade-sprint3` before `flask seed-community-demo` |
| P11, Safari CI | The job adds bounded waits, Simulator readiness checks, retries, and diagnostics. It still fails if any of the 8 pages is unchecked in either browser, overflows, or lacks expected content, or if iOS is not 390 px | Read the `safari-render` artifact. Do not use `continue-on-error` |

The latest `main` CI run, [45063727705](https://github.com/ReginaldBell/csce4905-it-capstone/actions/runs/45063727705), failed `safari-render`: desktop Safari
checked 2 of 8 pages and iOS checked 0. TC-604 stays Not run. A passing job is evidence
for that case, not a replacement for its full written procedure.

### Sprint 3 troubleshooting

| Symptom | Check / action |
|---|---|
| Missing-column error for a Sprint 3 field | Confirm the target database, back up, and run `flask upgrade-sprint3`. |
| `No such command "upgrade-sprint3"` | The running code does not include Sprint 3. Check the checkout and rebuild. |
| No reset email arrives | Check `MAIL_BACKEND`, `APP_BASE_URL`, whether the container received the SMTP settings, and the web logs. `console` sends nothing outside debug or testing, and requests over the limit send nothing. |
| Reset link has the wrong host | Set `APP_BASE_URL` to the site's address and recreate the web container. |
| Users are logged out after a password reset | Expected: `session_version` changed. They must sign in again. |
| Reset link returns 400 | The link is invalid, expired, used, replaced by a newer request, or canceled by an email change or reset. Request a new one. |
| Valid users get status 429 | Check the failed-attempt window and whether users share one `remote_addr`. |
| Photo returns 404 or redirects to login | Confirm the stored `photo_path` and the viewer. Non-owners need a report that is shared and `open`. Rewritten paths such as `/static/./uploads/<file>` get the same check. TC-107 passed on November 22, 2026. |

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | Codex | Document Sprint 2 setup, data lifecycle, configuration, preservation rules, verification, and operational limits. |
| 2026-11-21 | Claude | Add the community upgrade step and Material 3 UI files for the unmerged UI branch. |
| 2026-11-21 | Claude | Add the manual pre-upgrade backup procedure and its limits. |
| 2026-11-21 | Claude | Add Sprint 3 upgrade order, backup, environment, and troubleshooting; correct the photo access statement, implemented on `sprint3/integration`, not merged. |
| 2026-11-21 | Claude | Apply contract Addenda A and B: mail settings, console behavior, sessions, and troubleshooting, implemented on `sprint3/integration`, not merged. |
| 2026-11-21 | Claude | Apply integration corrections and contract Addenda C and D: mail fallbacks, unforwarded limit settings, upgrade columns, and photo paths, implemented on `sprint3/integration`, not merged. |
| 2026-11-22 | Claude | Replace pending Sprint 3 status with recorded automated, QA, and owner-check evidence. |
| 2026-11-22 | Claude | Record the official Sprint 3 run: 22 Pass and 5 Not run, with the 390 px heading overflow fixed. |
| 2026-11-22 | IT Capstone Team (B) | Document pending patches P1-P11: reset mail, verified TLS, background SMTP, atomic limits, comments, measurements, seed prerequisite, and Safari CI. |
| 2026-11-22 | IT Capstone Team (B) | Record Sprint 3 as merged through PRs #24 and #25, not deployed or sponsor accepted, with P1-P11 still pending. Add the P7 entry point. |
