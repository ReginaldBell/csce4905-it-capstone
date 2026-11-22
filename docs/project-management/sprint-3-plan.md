# Sprint 3 Plan: Profiles, Accounts, and Privacy

**Status:** Implemented on `sprint3/integration`, not merged; 180 automated tests passed; 22 of 27 Sprint 3 cases passed and 5 are Not run | **Sprint dates:** November 7 to December 3, 2026

**Owners:** _TBD_ | **Updated:** November 22, 2026 | **Sponsor approval:** _TBD_

## Goal

Secure private photos and complete the pet, contact, and account details that later
features use. This scope comes from the team's Sprint 2 Requirements document and
Sprint 2 Reflection.

Card IDs are plan IDs, not GitHub issue or PR numbers. The
[definition of done](kanban.md#definition-of-done) applies to every card.

## Sprint 3 cards

| Card | Title | Priority | IDs | Test cases | Current state |
|---|---|---|---|---|---|
| S3-01 | Merge the nearby feed and Material 3 UI to `main` | Lower, required first | Baseline | Unit tests | Snapshot committed at `5be8fa7`, the Sprint 3 base; not merged to `main` |
| S3-02 | Protect private photo links and retest access | High | NF2 | TC-104, TC-107 | Implemented and bypass fixed; TC-104 and TC-107 passed November 22, 2026 |
| S3-03 | Finish pet identifying fields | High | R2-R4 | TC-101 to TC-106, TC-108, TC-1003 to TC-1006 | Implemented; test cases passed November 22, 2026 |
| S3-04 | Add contact addresses | High | R8-R9 | TC-301 to TC-303 | Implemented; test cases passed November 22, 2026 |
| S3-05 | Let owners edit account details | High | R17, NF5 | TC-004 | Implemented; test cases passed November 22, 2026 |
| S3-06 | Add transactional email for reset links | High | R23 | TC-005 | Console, memory, and SMTP backends implemented; real delivery is in the backlog |
| S3-07 | Add password reset | High | R23, NF1 | TC-005, TC-1001 | Implemented; test cases passed November 22, 2026 |
| S3-08 | Limit repeated sign-in and reset requests | High | NF14 | TC-609, TC-1014 | Sign-in and reset limits implemented and passing; filing and tip limits are in the backlog; TC-609 and TC-1014 stay Not run |
| S3-09 | Validate the login redirect | High | NF2, R1 | TC-001 to TC-003, TC-1002 | Implemented; test cases passed November 22, 2026 |
| S3-10 | Fix phone navigation and page overflow | High | NF8 | TC-604 | Overflow fixed; Chrome and Edge passed at 390 and 1280 px; Firefox reported passing; latest `main` CI checked 2 of 8 desktop Safari pages and 0 iOS pages; TC-604 stays Not run |
| S3-11 | Check forms and keyboard use | High | NF5, NF12 | TC-605, TC-607 | Implemented; available checks passed; TC-605 needs report editing and TC-607 needs tips |
| S3-12 | Run Sprint 3 cases and finalize documents | High | All above | 27 assigned cases | Official run recorded: 22 Pass, 5 Not run |

S3-09 covers only the `next` redirect after login. Registration keeps its visible
duplicate-email error because TC-002 requires a clear error for a used email.

## Review patches

Review findings P1-P11 are on `sprint3-fix/*` branches, pending integration and
verification. See [PROJECT_STATE.md](../../PROJECT_STATE.md#sprint-3-review-patches).
They do not change any recorded test outcome.

## Backlog

The project owner moved these items to the backlog on November 21, 2026. They are not
complete and are not Sprint 3 commitments.

| Item | Suggested target | Needed to close |
|---|---|---|
| Real email delivery | Sprint 4, with the first QA deploy | Choose a provider and sending address, set `APP_BASE_URL` and `MAIL_*`, and deliver a reset email to a test inbox. Local reset emails print to the app console until then. |
| Upgrade the existing local database | Before this build runs on `infra_pgdata` | Back up the database and photos, run `flask init-db`, `flask upgrade-community`, and `flask upgrade-sprint3`, then confirm record counts. |
| Report-filing and tip request limits | Sprint 4 | Build the limits with their features, then finish TC-609 and TC-1014. |
| Finish remaining Sprint 3 cases | Safari now; others in Sprint 4 | Fix and verify Safari CI (P11), run TC-604 in Safari, TC-605 after report editing, and TC-607 after tips. |

## Sprint 4 bucket

The project owner moved these later-sprint features into Sprint 4 on November 22, 2026
because the remaining Sprint 3 cases depend on them.

| Feature | Requirement | Closes or supports |
|---|---|---|
| Report editing | R22 | TC-605 |
| Public report page for an open shared report | Part of R18-R19 | TC-607 precondition |
| Private tips with sign-in, owner-only reading, and unread counts | R21 | TC-607 |
| Report-filing request limits | NF14 | TC-609, TC-1014 |
| Tip request limits | NF14 | TC-609, TC-1014 |

ZIP search, the full guest Nearby feed, flagging, and Found Pet stay on their existing
schedule unless the team moves them.

## Later MVP work

These items stay on the roadmap but are not Sprint 3 commitments. Target sprints follow
the team's Requirements document where a requirement exists.

| Item | Priority | Target | Requirement |
|---|---|---|---|
| Harden deployment defaults and require a real secret key | High | Sprint 4, before first QA deploy | NF3 support |
| Verify and re-encode uploaded photos, removing location metadata | High | Sprint 4 | NF2, NF7 |
| Full guest Nearby browsing and ZIP search | High | Sprint 5 | R18-R19 |
| Approximate public locations | High | Sprint 5 | R18, NF2 |
| Private tips, with sign-in required to send | High | Sprint 4 | R21 |
| Flagging and reviewer controls | High | Sprints 4-5 | R24 |
| Owner notification email | High | Sprint 5 | Proposed; not in requirements |
| Owner removal of comments on their reports | High | Sprint 5 | Proposed; not in requirements |
| Landing page | High | Sprint 5 | Proposed; not in requirements |
| Account deletion, privacy policy, and terms | High | Sprint 6 | Proposed; not in requirements |
| HTTPS, secure cookies, and security headers | High | Sprints 4-6 | NF3 |
| Flyer QR code | High | Sprint 6 | R14 |
| Cloud photo storage | Lower | Sprint 4 | R20, NF11 |
| Versioned migrations and CI | Lower | Sprint 4 | Supports NF13 and testing |
| Hosting, backups, and restore test | Lower | Sprints 4-6 | NF3, NF13 |
| Logging, monitoring, and error pages | Lower | Sprint 6 | Release support |
| Final release check and sponsor acceptance | Lower | Sprint 6 | R1-R25, NF1-NF15 |

## Decisions needed

| Decision | Needed before | Status |
|---|---|---|
| Email provider and sending address | Real email delivery backlog item | _TBD_ |
| Sign-in and reset request limits | S3-08 | Build defaults: 5 failed sign-ins per 15 minutes, 3 reset requests per hour; team approval _TBD_ |
| Registration duplicate-email response | S3-09 | Decided: keep the visible error because TC-002 requires it |
| Partial cases TC-607, TC-609, TC-1014 | S3-12 | Project owner approved November 21, 2026: record the Sprint 3 portion in tests and notes; outcome stays Not run until the full procedure runs |
| Other sessions after password reset | S3-07 | Project owner approved November 21, 2026: end them with `User.session_version` |
| Compose mail settings | S3-06 | Project owner approved November 21, 2026: `APP_BASE_URL` and `MAIL_*` are passed to `web` |
| Card owners | Now | _TBD_ |
| Whether proposed MVP items become requirements | Sprint 4 planning | _TBD_ |
| ZIP search versus the current map and radius feed | Sprint 5 | _TBD_; requirements specify ZIP, the branch uses coordinates |

## Course documents

The editable Sprint 3 package is kept outside this repository in
`Downloads\IT Capstone Team B Sprint 3`. It is a draft until the Sprint 3 cases are run
and the team completes the Reflection.

## Revision history

| Date | Author | Summary |
|---|---|---|
| 2026-11-21 | Claude | Create the Sprint 3 MVP production-readiness plan. |
| 2026-11-21 | Claude | Apply the project owner's priorities: security and product gaps High, all other cards Lower. |
| 2026-11-21 | Claude | Align Sprint 3 to the team's official scope and move remaining MVP work to its target sprints. |
| 2026-11-21 | Claude | Narrow S3-09 to login redirect validation, record the registration decision, and update card states to pending verification. |
| 2026-11-21 | Claude | Apply contract Addenda A and B: approved decisions, implemented on `sprint3/integration`, not merged. |
| 2026-11-21 | Claude | Add real email delivery, the existing database upgrade, and filing and tip limits to the backlog. |
| 2026-11-22 | Claude | Replace pending Sprint 3 status with recorded automated, QA, and owner-check evidence. |
| 2026-11-22 | Claude | Record the official Sprint 3 run: 22 Pass and 5 Not run, with the 390 px heading overflow fixed. |
| 2026-11-22 | Claude | Record the project owner's Firefox report; TC-604 stays Not run until Safari is tested. |
| 2026-11-22 | Claude | Move report editing, private tips, the public report page, and filing and tip limits into the Sprint 4 bucket. |
| 2026-11-22 | IT Capstone Team (B) | Record pending patches P1-P11 and the failing Safari CI result; TC-604 stays Not run. |
