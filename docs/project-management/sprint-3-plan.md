# Sprint 3 Plan: Profiles, Accounts, and Privacy

**Status:** In progress, on the Sprint 3 integration branch, pending verification; Sprint 3 test cases Not run | **Sprint dates:** November 7 to December 3, 2026

**Owners:** _TBD_ | **Updated:** November 21, 2026 | **Sponsor approval:** _TBD_

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
| S3-02 | Protect private photo links and retest access | High | NF2 | TC-104, TC-107 | Access check on the Sprint 3 integration branch, pending TC-107 as owner, another user, and guest |
| S3-03 | Finish pet identifying fields | High | R2-R4 | TC-101 to TC-106, TC-108, TC-1003 to TC-1006 | On the Sprint 3 integration branch, pending verification |
| S3-04 | Add contact addresses | High | R8-R9 | TC-301 to TC-303 | On the Sprint 3 integration branch, pending verification |
| S3-05 | Let owners edit account details | High | R17, NF5 | TC-004 | On the Sprint 3 integration branch, pending verification |
| S3-06 | Add transactional email for reset links | High | R23 | TC-005 | Console, memory, and SMTP backends on the Sprint 3 integration branch, pending verification; provider _TBD_ |
| S3-07 | Add password reset | High | R23, NF1 | TC-005, TC-1001 | On the Sprint 3 integration branch, pending verification |
| S3-08 | Limit repeated sign-in and reset requests | High | NF14 | TC-609, TC-1014 | Sign-in and reset limits on the Sprint 3 integration branch, pending verification; filing and tip limits are later work |
| S3-09 | Validate the login redirect | High | NF2, R1 | TC-001 to TC-003, TC-1002 | On the Sprint 3 integration branch, pending verification |
| S3-10 | Fix phone navigation and page overflow | High | NF8 | TC-604 | UI branch passed 412 and 768 px in Chrome; 390 px changes on the Sprint 3 integration branch, pending TC-604 in all browsers |
| S3-11 | Check forms and keyboard use | High | NF5, NF12 | TC-605, TC-607 | Label, error, and focus changes on the Sprint 3 integration branch, pending verification |
| S3-12 | Run Sprint 3 cases and finalize documents | High | All above | 27 assigned cases | All Not run |

S3-09 covers only the `next` redirect after login. Registration keeps its visible
duplicate-email error because TC-002 requires a clear error for a used email.

## Later MVP work

These items stay on the roadmap but are not Sprint 3 commitments. Target sprints follow
the team's Requirements document where a requirement exists.

| Item | Priority | Target | Requirement |
|---|---|---|---|
| Harden deployment defaults and require a real secret key | High | Sprint 4, before first QA deploy | NF3 support |
| Verify and re-encode uploaded photos, removing location metadata | High | Sprint 4 | NF2, NF7 |
| Public report pages and guest browsing | High | Sprint 5 | R18-R19 |
| Approximate public locations | High | Sprint 5 | R18, NF2 |
| Private tips, with sign-in required to send | High | Sprint 5 | R21 |
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
| Email provider and sending address | S3-06 | _TBD_ |
| Sign-in and reset request limits | S3-08 | Build defaults: 5 failed sign-ins per 15 minutes, 3 reset requests per hour; team approval _TBD_ |
| Registration duplicate-email response | S3-09 | Decided: keep the visible error because TC-002 requires it |
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
