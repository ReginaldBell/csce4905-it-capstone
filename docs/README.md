# Documentation

Lifecycle documents for the CSCE 4905/4925 IT Capstone project use the Unified
Process. The Sprint 2 application baseline is `4d51cc3` on November 4, 2026.
Implemented behavior is documented; sponsor approval, deployment, and formal
acceptance remain separate pending activities.

## Start here

- [Project state and change record](../PROJECT_STATE.md): living baseline, changes,
  decision index, pending work, and update procedure.
- [Sprint 2 delivery and decision record](project-management/sprint-2-record.md):
  delivered cards, PR/commit ledger, rationale, review defects/fixes, and evidence limits.
- [User manual](4-transition/user-manual.md): tasks and expected application behavior.
- [Maintenance manual](4-transition/maintenance-manual.md): local setup and operation.

## Lifecycle documents

| Phase | Document | Current purpose |
|---|---|---|
| Inception | [Vision and scope](1-inception/vision.md) | Sponsor-facing draft; unresolved items stay explicit |
| Inception | [Requirements](1-inception/requirements-srs.md) | Concrete Sprint 2 requirements and test traceability |
| Elaboration | [Use cases](2-elaboration/use-case-model.md) | Implemented user flows and alternates |
| Elaboration | [Architecture and design](2-elaboration/architecture-design.md) | Components, schema, interfaces, ownership, and design rules |
| Construction | [Test plan and results](3-construction/test-plan.md) | Reproducible cases and historical review evidence |
| Transition | [User manual](4-transition/user-manual.md) | End-user workflows and troubleshooting |
| Transition | [Maintenance manual](4-transition/maintenance-manual.md) | Setup, data, configuration, and handover limits |

## Project management

- [Kanban conventions](project-management/kanban.md): board columns, card rules, definition of done.
- [Sprint 2 record](project-management/sprint-2-record.md): preserve this as historical context.
- [PROJECT_STATE.md](../PROJECT_STATE.md): update when behavior, decisions, or project status changes.

## Conventions

- Markdown is the source format. Add a dated revision row for substantive changes.
- Sprint 2 requirement/use-case/test IDs use `FR-S2-xx`, `NFR-S2-xx`, `UC-S2-xx`,
  and `TC-S2-xx`. Decisions use `S2-Dxx`. These replace unfilled template examples,
  without claiming a sponsor-approved requirements baseline.
- Link requirements to use cases, design, and test cases. Distinguish card numbers
  from PR numbers.
- Keep unknowns as `_TBD_` and distinguish implementation, verification, deployment,
  and acceptance. Do not convert examples into approved requirements.
- Record actual test environments and limits; temporary review scripts/PDFs do not
  establish committed automation or CI.
- Diagram source may be inline Mermaid, as in the architecture document, or stored
  under `docs/diagrams/` when separate source/export files are needed.
- Update this index, the root README, and project state when adding major records.

## Revision history

| Date | Author | Summary |
|---|---|---|
| 2026-11-04 | Codex | Index the Sprint 2 documentation set and establish state/decision/traceability conventions. |
