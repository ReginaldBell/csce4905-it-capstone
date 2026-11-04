# Maintenance Manual

**Phase:** Transition | **Status:** Sprint 2 implementation documented; production handover _TBD_

**Owner:** _TBD_ | **Audience:** maintainers | **Baseline:** `4d51cc3`, November 4, 2026

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
| `src/static/css/app.css` | Shared screen styles and flyer print rules |
| `src/static/uploads/` | Runtime photos, ignored by Git except .gitkeep |
| `infra/docker-compose.yml` | Local database/web services and persistence |

## 3. Build and run locally

From the repository root:

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml exec web flask init-db
docker compose -f infra/docker-compose.yml ps
```

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
| Photo URL 404 | Check stored photo_path and corresponding upload file; database restoration alone is insufficient. |
| Wrong report time | Check selected-date timezone script, offset sign/bounds, browser timezone, and zero-offset fallback. |
| Empty report output redirects | Expected after all linked pets were deleted; retain report/history and shared guard. |
| Email/phone picker links wrong | Confirm generic pick_contact.html receives the correct target endpoint. |
| Flyer spans extra pages | Re-run the actual PDF fixture and check print settings/content; break avoidance alone does not guarantee arbitrary layouts fit. |
| Stale reminder includes wrong pets | Check owner filter and strict updated_at cutoff using a frozen clock/test data. |
| POST fails before route ownership check | Supply a valid token from that test user's own session; use separate sessions for isolation cases. |

## 8. Known limits and handover work

- Existing static photo URLs are directly accessible; owned application routes do
  not constitute private media delivery.
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

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | Codex | Document Sprint 2 setup, data lifecycle, configuration, preservation rules, verification, and operational limits. |
