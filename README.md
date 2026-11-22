# Pet Finder — CSCE 4905/4925 IT Capstone

Pet Finder helps owners maintain pet profiles, file missing-pet reports, manage
agency contacts, and prepare email, phone, social-media, and printable outreach
material. This is the UNT CSCE 4905/4925 BA Information Technology Capstone repository.

## Current state

Sprint 2 implementation cards 3–11 are merged through PRs #12–#20. The documented
application baseline is [`4d51cc3`](https://github.com/ReginaldBell/csce4905-it-capstone/commit/4d51cc3848699165b77513cad5ea797fc35f97e7)
on November 4, 2026. Sponsor acceptance and final delivery remain pending.

- Contacts: owner-scoped CRUD, category grouping, and inline validation.
- Reports: multiple owned pets, last-seen information, UTC conversion, status changes,
  and history.
- Outreach: agency email, phone script, social caption/photo downloads, and a printable
  flyer. Only flyer notes are shortened; stored notes remain complete.
- Reminders: a successful-login message for pets last updated more than 90 days ago.
- Existing account, pet CRUD, and photo-upload functionality is retained.

Sprint 3 work is on the Sprint 3 integration branch, pending verification. It covers pet
and contact details, account editing, password reset, sign-in and reset limits, photo
access checks, and usability fixes. It is not on `main`, and its test cases are Not run.

Start with [PROJECT_STATE.md](PROJECT_STATE.md) for the living status, change log,
decisions, and pending work. The [Sprint 2 record](docs/project-management/sprint-2-record.md)
contains the detailed decisions, dependencies, merged PRs, and review fixes.

## Run locally

Install Docker with Compose, then run from the repository root:

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml exec web flask init-db
docker compose -f infra/docker-compose.yml exec web flask upgrade-community
```

Open [the login page](http://localhost:5000/login) and register an account. There is
no application landing route at `/`; use `/login`, `/pets`, or `/reports`.

`flask init-db` creates missing tables; it does not clear data or migrate existing
columns. `flask upgrade-community` adds the nearby-feed columns to an older database,
keeps existing records, and is safe to run again. The database uses a named volume;
photos live in `src/static/uploads/`.
See the [maintenance manual](docs/4-transition/maintenance-manual.md) before changing
the environment. The supplied Compose configuration is for local development.

### Sprint 3 branch

Back up first by following the
[Sprint 3 upgrade steps](docs/4-transition/maintenance-manual.md#9-sprint-3-upgrade-and-operations).
By default, every checkout uses the same `infra_pgdata` database volume. After the setup
commands above, run:

```bash
docker compose -f infra/docker-compose.yml exec web flask upgrade-sprint3
```

Password reset emails print to the web logs unless a mail backend is configured. To run
the automated tests, see the [test plan](docs/3-construction/test-plan.md#how-to-run-the-automated-suite).

## Documentation

| Document | Purpose |
|---|---|
| [Project state](PROJECT_STATE.md) | Living status, change/decision index, pending work, and update rules |
| [Sprint 2 record](docs/project-management/sprint-2-record.md) | Delivery ledger, design decisions, dependencies, fixes, and verification limits |
| [Sprint 3 plan](docs/project-management/sprint-3-plan.md) | Official Sprint 3 scope, later MVP work by target sprint, and open decisions |
| [Documentation index](docs/README.md) | Lifecycle document map |
| [Requirements](docs/1-inception/requirements-srs.md) | Delivered requirements and traceability; sponsor approval pending |
| [Use cases](docs/2-elaboration/use-case-model.md) | User workflows and alternate flows |
| [Architecture and design](docs/2-elaboration/architecture-design.md) | Components, schema, routes, and ownership |
| [Test plan and results](docs/3-construction/test-plan.md) | Reproducible checks and historical review evidence |
| [User manual](docs/4-transition/user-manual.md) | End-user instructions |
| [Maintenance manual](docs/4-transition/maintenance-manual.md) | Setup, data, operations, and limitations |
| [Kanban conventions](docs/project-management/kanban.md) | Board columns and definition of done |
| [Vision and scope draft](docs/1-inception/vision.md) | Sponsor-facing definition still awaiting completion |

## Repository layout

```text
src/                  Flask application, models, templates, and static assets
infra/                Local Docker Compose configuration
docs/                 Lifecycle documentation and sprint records
PROJECT_STATE.md      Living status and change/decision index
Dockerfile            Python 3.12 development application image
requirements.txt      Pinned Python dependencies
```

The application uses Flask, SQLAlchemy, Flask-Login, Flask-WTF, Jinja, and PostgreSQL
16. Review checks used disposable PostgreSQL and isolated SQLite/Flask snapshots,
plus Chrome print-to-PDF checks. A committed automated test suite and CI pipeline
are not part of this baseline; the test plan records what was actually verified.

## Team and working agreement

| Item | Current record |
|---|---|
| Team member | Reggie Bell — [@ReginaldBell](https://github.com/ReginaldBell) |
| Course | CSCE 4905 (Fall) → CSCE 4925 (Spring) |
| Sponsor / contact | _TBD_ |
| Technical reviewer | _TBD_ |
| Instructor | _TBD_ |
| Formal roles and additional members | _TBD_ |

Work starts from a scoped board card and a branch. Changes go through reviewed
pull requests, with affected documentation updated alongside the implementation.
Sprint 2 PRs used merge commits and source-branch deletion. Preserve earlier
features when reconciling independently developed changes.

When the project changes, update `PROJECT_STATE.md`, the relevant lifecycle
documents, and the applicable sprint record. Keep pending decisions distinct
from approved requirements.

## Revision history

| Date | Author | Summary |
|---|---|---|
| 2026-11-04 | Reginad Bell | Document delivered Sprint 2 features, local setup, project-state links, and verification scope. |
| 2026-11-21 | Claude | Add the community upgrade step and link the Sprint 3 plan. |
| 2026-11-21 | Claude | Add Sprint 3 status and run steps, on the Sprint 3 integration branch, pending verification. |
