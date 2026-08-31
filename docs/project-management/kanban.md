# Kanban Board

The team runs its work on a single GitHub Project board attached to this repository.
The board is the source of truth for who is doing what.

## Columns

| Column | Meaning | WIP limit |
|---|---|---|
| **Backlog** | Everything identified but not yet ready to start. No owner required. | — |
| **Ready** | Scoped, understood, and unblocked. Anyone can pull from here. | — |
| **In Progress** | Actively being worked. Every card here has exactly one owner. | 1–2 per person |
| **In Review** | Pull request open, or document waiting on sponsor/reviewer feedback. | 4 |
| **Blocked** | Waiting on something outside the team (sponsor answer, access, hardware). Card must say what it is waiting on. | — |
| **Done** | Merged and meets the definition of done. | — |

Work flows left to right and is **pulled**, not assigned: when you finish a card, you take
the top card from Ready rather than being handed one.

## Card rules

- One card = one deliverable-sized piece of work, ideally finishable in under a week.
- Every card has a title in imperative form, a description, an owner (once In Progress),
  and a label.
- Cards that trace to a requirement or document reference it by ID (`FR-03`, `UC-02`, `TC-07`).
- If a card sits in Blocked for more than two days, raise it at standup or with the sponsor.

## Labels

| Label | Use |
|---|---|
| `docs` | Lifecycle documents (Vision, SRS, design, test plan, manuals) |
| `feature` | New system functionality |
| `bug` | Defect found in testing or review |
| `infra` | Environments, tooling, deployment, hardware |
| `research` | Spike or investigation with a written outcome |
| `admin` | Course deliverables, presentations, sponsor coordination |
| `blocked` | Mirrors the Blocked column for filtering |

## Definition of done

A card moves to Done only when all of these are true:

1. The work is complete and merged to `main` through a reviewed pull request.
2. Any affected UP document in [`docs/`](../) has been updated in the same PR.
3. Tests that cover the change pass (once `tests/` exists).
4. A teammate other than the author has reviewed it.
5. Nothing about the card is still `_TBD_`.

## Cadence

| Ritual | When | Purpose |
|---|---|---|
| Standup | _TBD_ (2×/week, 15 min) | What moved, what's next, what's blocked |
| Board grooming | Weekly | Break down Backlog cards, re-prioritize Ready |
| Sponsor check-in | _TBD_ | Validate requirements and review documents |
| Phase review | End of each UP phase | Confirm phase deliverables are complete before moving on |

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft |
