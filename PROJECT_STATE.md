# Project State and Change Record

**Updated:** November 4, 2026

**Application baseline:** [`main` at `4d51cc3`](https://github.com/ReginaldBell/csce4905-it-capstone/commit/4d51cc3848699165b77513cad5ea797fc35f97e7)

This is the living record of what exists, what changed, which decisions apply,
and what still needs a decision or verification. The application baseline is
separate from subsequent documentation edits. Merge review is not sponsor
acceptance or production deployment.

## Current status

| Area | State | Detail |
|---|---|---|
| Sprint 1 foundation | Retained | Account flows, pet CRUD, and photo uploads |
| Sprint 2 cards 3–11 | Merged and reviewed | PRs #12–#20; [delivery ledger](docs/project-management/sprint-2-record.md#delivery-ledger) |
| Final Sprint 2 fix | Merged | Flyer-only notes excerpt; one-page long-notes repro verified in Chrome |
| Source branches for PRs #12–#20 | Deleted after merge | Recorded in the review/merge sessions |
| Documentation | Sprint 2 catch-up recorded | Requirements, use cases, design, results, manuals, and this file |
| Verification | Focused review cases passed | [Test plan](docs/3-construction/test-plan.md); no committed CI suite claimed |
| Sponsor acceptance / final course delivery | _TBD_ | No acceptance sign-off established in the review record |
| Production hosting, operating owner, support | _TBD_ | Local development configuration exists |

## Delivered behavior

- Owner-scoped contacts, pets, and reports with authentication and CSRF protection
  on form submissions.
- Missing-pet reports covering one or more owned pets, required location, optional
  local sighting time converted to UTC, and full notes.
- `open`, `found`, and `closed` transitions with event history.
- Email, phone script, social caption/photo downloads, and printable flyer generated
  from current saved data.
- Flyer notes capped at 200 displayed characters; full notes retained in storage,
  report detail, email, phone script, and social post.
- One informational login reminder for the owner's pets updated strictly more than
  90 days ago.

The [user manual](docs/4-transition/user-manual.md) describes the workflows;
[architecture](docs/2-elaboration/architecture-design.md) describes implementation.

## Change log

All entries below belong to the November 4, 2026 Sprint 2 implementation review.
Plan card numbers are different from PR numbers.

| Change | PR | Merge | Result |
|---|---|---|---|
| Reports schema, card 4 | [#12](https://github.com/ReginaldBell/csce4905-it-capstone/pull/12) | `4ea6b5e` | Additive models; no routes/templates in this PR |
| Contacts schema/CRUD, card 3 | [#13](https://github.com/ReginaldBell/csce4905-it-capstone/pull/13) | `1a5e280` | Includes validation fixes and model reconciliation |
| Report form, card 5 | [#14](https://github.com/ReginaldBell/csce4905-it-capstone/pull/14) | `801821a` | UTC, selected-date DST, and offset-bound fixes |
| Status/history, card 11 | [#15](https://github.com/ReginaldBell/csce4905-it-capstone/pull/15) | `4f7cea4` | Initial event, transitions, closure time, no-op |
| Agency email, card 6 | [#16](https://github.com/ReginaldBell/csce4905-it-capstone/pull/16) | `a429109` | Empty-pets guard; status/history preserved |
| Login reminder, card 10 | [#20](https://github.com/ReginaldBell/csce4905-it-capstone/pull/20) | `a6e6783` | Independent `auth.py` change |
| Phone script, card 7 | [#17](https://github.com/ReginaldBell/csce4905-it-capstone/pull/17) | `18acacb` | Shared contact picker with email |
| Social/photo output, card 8 | [#18](https://github.com/ReginaldBell/csce4905-it-capstone/pull/18) | `f2615b1` | Phone and social output retained together |
| Printable flyer, card 9 | [#19](https://github.com/ReginaldBell/csce4905-it-capstone/pull/19) | `4d51cc3` | Long-notes/photo repro reduced from four pages to one |

## Active decisions

The detailed rationale and fix history live in the
[Sprint 2 decision log](docs/project-management/sprint-2-record.md#decision-log).

| ID | Current rule |
|---|---|
| S2-D01 | Contacts table creation belongs with Contacts CRUD; report schema remains a separate deliverable. |
| S2-D02 | Reports may link multiple pets; deleting a pet removes links while retaining reports/history. |
| S2-D03 | Scope application records by owner; check report and contact IDs independently. |
| S2-D04 | Inline server validation; email at most 255 characters; phone requires a digit. |
| S2-D05 | Convert selected-date local sighting time to UTC with offset in `[-840, 720]`. |
| S2-D06 | Log actual status transitions; same-status submissions do not alter history or closure time. |
| S2-D07 | Generate outputs on demand; no saved generated-text records or automatic sending. |
| S2-D08 | Email/phone share a contact picker; social/flyer need no contact. |
| S2-D09 | Retain reports with no remaining pets; redirect output requests with an explanation. |
| S2-D10 | Shorten only flyer notes to at most 200 characters; keep complete notes elsewhere. |
| S2-D11 | Use browser copy, download, mailto, and print features. |
| S2-D12 | Inform at successful login when own pets are strictly older than 90 days. |
| S2-D13 | Add missing tables without resetting data; schema alterations need a migration plan. |
| S2-D14 | Review each PR, preserve upstream work during reconciliation, use merge commits and branch cleanup. |

Changing an active rule requires a documented implementation change and regression
evidence; these entries describe the delivered baseline, not unapproved future work.

## Pending work and verification limits

| Item | Next action | Current evidence |
|---|---|---|
| Repeatable tests / CI | Turn recorded cases into a maintained suite and pipeline | Review harnesses were temporary; no committed suite in this baseline |
| Sponsor-facing scope / approval | Complete vision, confirm requirements, record acceptance | _TBD_ |
| Production operation | Choose hosting, secrets, backup/restore owner, support, and deployment process | _TBD_; local Compose only |
| Browser coverage | Exercise clipboard permission/failure paths and a defined browser matrix | Handlers inspected; not a browser certification |
| Print coverage | Retest supported page/printer settings and representative content | Specific Chrome long-notes repro is one page; arbitrary layouts not certified |
| Time fallback | Decide whether missing/non-numeric offsets should continue to mean UTC | Currently zero offset; JavaScript needed for automatic local conversion |
| Uploaded media policy | Confirm future access and retention requirements | Static photo URLs remain directly accessible, inherited from earlier code |

These are follow-up work or recorded limits, not unresolved blockers left on the
merged Sprint 2 PRs. Assignees, deadlines, production status, and sponsor decisions
remain unassigned unless explicitly established.

## Update procedure

1. Update the date and application baseline after a reviewed merge.
2. Add a change-log row with PR, merge commit, and observable behavior.
3. Record decision changes and rationale in the relevant sprint record.
4. Update affected requirements, use cases, design, test evidence, and manuals.
5. Resolve a pending item only when evidence exists; link that evidence.
6. Keep implementation, verification, deployment, and acceptance distinct.

## Revision history

| Date | Author | Summary |
|---|---|---|
| 2026-11-04 | Codex | Establish living project state, Sprint 2 change/decision index, and pending-work register. |
