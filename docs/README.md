# Documentation

Lifecycle documents for the CSCE 4905/4925 IT Capstone project, organized by
**Unified Process** phase. Each document starts as a template — fill it in, keep it current,
and update it in the same pull request as the work it describes.

## Phases

### 1 — Inception
Define the problem, agree on scope with the sponsor, and capture requirements.
- [`vision.md`](1-inception/vision.md) — problem statement, scope, stakeholders, success criteria
- [`requirements-srs.md`](1-inception/requirements-srs.md) — functional and non-functional requirements

### 2 — Elaboration
Nail down behavior and architecture; retire the highest technical risks.
- [`use-case-model.md`](2-elaboration/use-case-model.md) — actors, use cases, main and alternate flows
- [`architecture-design.md`](2-elaboration/architecture-design.md) — architecture, components, data model, interfaces

### 3 — Construction
Build the system in iterations and prove it works.
- [`test-plan.md`](3-construction/test-plan.md) — test strategy, cases, traceability, results

### 4 — Transition
Hand the system over.
- [`user-manual.md`](4-transition/user-manual.md) — how an end user operates the system
- [`maintenance-manual.md`](4-transition/maintenance-manual.md) — how a future team runs, fixes, and extends it

## Project management
- [`project-management/kanban.md`](project-management/kanban.md) — board columns, card rules, definition of done

## Document conventions

- Markdown only; one document per file.
- Every document carries a revision history table at the bottom — add a row on each
  substantive change (date, author, summary).
- Requirements get stable IDs (`FR-01`, `NFR-01`, `UC-01`) and those IDs are what test
  cases and design sections reference.
- Mark anything unresolved as `_TBD_` rather than deleting the heading, so gaps stay visible.
- Diagrams: source in `docs/diagrams/` where possible, exported image committed alongside.
