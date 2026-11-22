# Project State and Change Record

**Updated:** November 22, 2026

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
| Material 3 UI | Included in `sprint3/integration`; not merged or peer reviewed | Figma-based reskin of the missing-pet app, built on the nearby feed branch |
| Local database | Community upgrade only | `flask upgrade-community` ran on `infra_pgdata` on November 21, 2026 after a `pg_dump` backup, with record counts unchanged. The Sprint 3 upgrade is in the backlog. |
| Sprint 3 QA database | Upgraded November 22, 2026 | Isolated `petfinder-qa` PostgreSQL 16 database and photo volume. A backup was taken, `flask upgrade-sprint3` ran twice, and record counts stayed at 12 users, 25 pets, 24 reports, and 8 comments. Demo sign-in and the main Sprint 3 pages loaded at `http://127.0.0.1:5001`. |
| Sprint 3 (November 7 to December 3, 2026) | Implemented on `sprint3/integration`, not merged; 180 automated tests passed; 22 of 27 Sprint 3 test cases passed on November 22, 2026; TC-604, TC-605, TC-607, TC-609, and TC-1014 remain Not run | [Sprint 3 plan](docs/project-management/sprint-3-plan.md): photo privacy, pet and contact details, account updates and recovery, usability; backlog holds real email delivery, the existing database upgrade, and filing and tip limits; later MVP work is mapped to Sprints 4-6; owners and board entries are _TBD_ |
| Sprint 3 review patches | On `sprint3-fix/*`; pending integration and verification | [P1-P11](#sprint-3-review-patches); none recorded as passed, merged, or deployed |
| Safari CI | Failing on latest `main` run | [Run 45063727705](https://github.com/ReginaldBell/csce4905-it-capstone/actions/runs/45063727705) at `8038dc8`: `unit-tests` passed; `safari-render` checked 2 of 8 desktop pages and 0 iOS pages |
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
| Repeatable tests / CI | Integrate and verify the P11 Safari CI patch, then get a passing `main` run | `main` at `8038dc8` has a CI workflow. In [run 45063727705](https://github.com/ReginaldBell/csce4905-it-capstone/actions/runs/45063727705), `unit-tests` passed and `safari-render` failed |
| Sponsor-facing scope / approval | Complete vision, confirm requirements, record acceptance | _TBD_ |
| Production operation | Choose hosting, secrets, backup/restore owner, support, and deployment process | _TBD_; local Compose only |
| Browser coverage | Exercise clipboard permission/failure paths and a defined browser matrix | Handlers inspected; not a browser certification |
| Print coverage | Retest supported page/printer settings and representative content | Specific Chrome long-notes repro is one page; arbitrary layouts not certified |
| Time fallback | Decide whether missing/non-numeric offsets should continue to mean UTC | Currently zero offset; JavaScript needed for automatic local conversion |
| Uploaded media policy | Confirm future access and retention requirements | On `main`, uploaded photo URLs are directly accessible. On the Sprint 3 branch, they are access-checked, and TC-107 passed on November 22, 2026: owners keep access, and non-owners need a shared, open report |
| Sprint 3 verification | Finish the 5 remaining cases | November 22, 2026: 22 Pass, 0 open failures, 5 Not run. TC-604 needs Safari: the latest `main` CI run checked 2 of 8 desktop Safari pages and 0 iOS Safari pages. The project owner reported Firefox passing. TC-605, TC-607, TC-609, and TC-1014 depend on features now in the Sprint 4 bucket. See the [test plan](docs/3-construction/test-plan.md#9-sprint-3-test-cases) |
| Sprint 3 schema upgrade | Back up, then run `flask upgrade-sprint3` on the intended database | Not recorded as run on a shared or deployed database |
| Sprint 3 mail configuration | Choose provider and sending address; set `APP_BASE_URL` and SMTP values outside the repository | Provider _TBD_; Compose passes `APP_BASE_URL` and `MAIL_*`; real email delivery is untested and in the backlog |
| Sprint 3 partial cases | Keep TC-607, TC-609, and TC-1014 open until tips and filing limits exist | Project owner approved November 21, 2026; outcomes stay Not run until each full procedure runs |
| Material 3 design fidelity | Compare against exact Figma specs when plan limits allow | Built from Figma layout sizes, an overview screenshot, dialog specs, and Material 3 baseline tokens; not a verified pixel match |
| Material 3 UI verification | Commit, review, and merge the branch, then repeat on the target environment | November 21, 2026: 26 unit tests passed; disposable PostgreSQL upgrade from `4d51cc3` kept records; Chrome checked photos, map, settings, and a one-page flyer; signed-in pages loaded on the upgraded local database; the project owner reported a hands-on local test with no problems (individual cases not itemized) |
| Backup restore | Test restoring the November 21, 2026 local dump in an isolated database | Dump created and checked as complete; restore not tested; uploaded photos are not in the dump |
| Adoption alerts | Decide whether notifications are in scope | Design-only setting; omitted because the app has no notification system |

These are follow-up work or recorded limits, not unresolved blockers left on the
merged Sprint 2 PRs. Assignees, deadlines, production status, and sponsor decisions
remain unassigned unless explicitly established.

## Sprint 3 review patches

These findings came from the Sprint 3 review of `main` at `8038dc8`. Each fix is assigned
to a `sprint3-fix/*` branch. **None is recorded as passed, merged, or deployed.** Until a
row has linked evidence, the behavior on `main` is unchanged.

| ID | Finding | Intended behavior | Branch | State |
|---|---|---|---|---|
| P1 | Reset links could use an untrusted request host | Use `APP_BASE_URL`. Without it, only debug or testing with `console` or `memory` may build a link. `smtp` without it sends nothing, even in debug | `sprint3-fix/auth` | Pending integration and verification |
| P2 | SMTP TLS did not verify the server | STARTTLS uses the default certificate and hostname checks | `sprint3-fix/auth` | Pending integration and verification |
| P3 | Concurrent sign-ins could pass the limit | Reserve an attempt atomically before any password check | `sprint3-fix/auth` | Pending integration and verification |
| P4 | Concurrent reset requests could pass the limit | Reserve an attempt atomically. Blocked retries send nothing and do not extend the block | `sprint3-fix/auth` | Pending integration and verification |
| P5 | A concurrent email change could return a 500 | Show the inline email-taken error and roll back | `sprint3-fix/data` | Pending integration and verification |
| P6 | Very small measurements could display in exponent notation | A saved `0.00001` prefills as `0.00001` and survives an unrelated edit | `sprint3-fix/data` | Pending integration and verification |
| P7 | Authors could not delete a comment after unsharing | The author can delete their own comment. Other requests get 404, and unsharing still hides the post and comments from others. No page lists these comments after unsharing, so the delete control is reachable only from a post page already open | `sprint3-fix/data` | Pending integration and verification |
| P8 | A slow SMTP server could delay reset responses and reveal whether an account exists | SMTP reset mail sends in the background. Failures log only the error type | `sprint3-fix/auth` | Pending integration and verification |
| P9 | Registration did not apply the email length limit | Show a field error on `email`, with no 500 | `sprint3-fix/auth` | Pending integration and verification |
| P10 | Seeding could fail without naming the upgrade steps | Name `flask upgrade-community` and `flask upgrade-sprint3`. Exit nonzero without a partial seed if Sprint 3 pet columns are missing | `sprint3-fix/data` | Pending integration and verification |
| P11 | The Safari CI job failed before checking every page | Use bounded waits, Simulator readiness checks, retries, and diagnostics. Fail if any of the 8 pages is unchecked in either browser | `sprint3-fix/ci` | Pending integration and verification |

Operating details are in the
[maintenance manual](docs/4-transition/maintenance-manual.md#pending-review-patches).
A passing Safari CI job would be evidence for TC-604, but the case stays **Not run** until
its full written procedure runs. The recorded Sprint 3 result remains 22 Pass and 5 Not run.

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
| 2026-11-21 | Claude | Record the unmerged Material 3 UI branch, its verification evidence, and remaining design and scope items. |
| 2026-11-21 | Claude | Record the local database upgrade, backup limits, and the project owner's local test. |
| 2026-11-21 | Claude | Add the planned Sprint 3 MVP production-readiness work. |
| 2026-11-21 | Claude | Align Sprint 3 status to the team's official requirements. |
| 2026-11-21 | Claude | Record Sprint 3 work implemented on `sprint3/integration`, not merged, its open items, and the corrected photo access statement. |
| 2026-11-21 | Claude | Apply contract Addenda A and B: mail status, photo rule, and partial cases, implemented on `sprint3/integration`, not merged. |
| 2026-11-22 | Claude | Replace pending Sprint 3 status with recorded automated, QA, and owner-check evidence. |
| 2026-11-22 | Claude | Record the official Sprint 3 run: 22 Pass and 5 Not run, with the 390 px heading overflow fixed. |
| 2026-11-22 | Claude | Record the project owner's Firefox report; TC-604 stays Not run until Safari is tested. |
| 2026-11-22 | Claude | Move report editing, private tips, the public report page, and filing and tip limits into the Sprint 4 bucket. |
| 2026-11-22 | IT Capstone Team (B) | Record review patches P1-P11 on `sprint3-fix/*`, pending integration and verification, and the failing Safari CI result; TC-604 stays Not run. |
