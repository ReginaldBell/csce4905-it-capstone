# CSCE 4905/4925 — IT Capstone

Team project repository for the UNT **CSCE 4905/4925 BA Information Technology Capstone** sequence.
The capstone runs across two semesters and carries a project through the full development
lifecycle — from requirements through delivery — using the **Unified Process (UP)** for the
lifecycle documents and a **Kanban** board for day-to-day work.

---

## Project

| | |
|---|---|
| **Project name** | _TBD_ |
| **One-line description** | _TBD_ |
| **Sponsor / contact** | _TBD_ (requirements validation contact) |
| **Technical reviewer** | _TBD_ (reviews design, test, and manual documents) |
| **Course** | CSCE 4905 (Fall) → CSCE 4925 (Spring) |
| **Instructor** | _TBD_ |

> Sponsored projects must be registered with the UNT College of Engineering —
> see <https://engineering.unt.edu/capstone>.

## Team

| Name | Role | GitHub | Contact |
|---|---|---|---|
| Reggie Bell | _TBD_ | @ReginaldBell | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

Roles to cover across the team: project manager, requirements lead, architect/design lead,
development lead, test lead, documentation lead.

## Documentation (Unified Process)

All lifecycle documents live in [`docs/`](docs/), organized by UP phase:

| Phase | Documents |
|---|---|
| **1 — Inception** | [Vision & Scope](docs/1-inception/vision.md) · [Requirements (SRS)](docs/1-inception/requirements-srs.md) |
| **2 — Elaboration** | [Use Case Model](docs/2-elaboration/use-case-model.md) · [Architecture & Design](docs/2-elaboration/architecture-design.md) |
| **3 — Construction** | [Test Plan](docs/3-construction/test-plan.md) |
| **4 — Transition** | [User Manual](docs/4-transition/user-manual.md) · [Maintenance Manual](docs/4-transition/maintenance-manual.md) |

Board conventions are documented in [`docs/project-management/kanban.md`](docs/project-management/kanban.md).

## Repository layout

```
.
├── README.md
├── docs/                  # UP lifecycle documents (see table above)
├── src/                   # application source (added once the stack is chosen)
├── tests/                 # automated tests
└── infra/                 # configs, scripts, deployment / network artifacts
```

## Working agreement

- **Board first.** Every piece of work has a card on the Kanban board before it starts.
- **Branch per card.** `feature/<card-#>-short-name`, `docs/<card-#>-short-name`, `fix/<card-#>-short-name`.
- **Pull requests only.** `main` is protected; every change merges through a PR with at
  least one teammate's review.
- **Small commits, clear messages.** Present tense, reference the card: `docs: draft SRS section 3 (#12)`.
- **Document as you build.** A feature is not done until the matching UP document is updated.

## Getting started

Nothing to build yet — the technology stack is chosen during Inception and this section
gets filled in with setup, run, and test instructions once `src/` exists.

```bash
git clone https://github.com/ReginaldBell/csce4905-it-capstone.git
cd csce4905-it-capstone
```
