# Test Plan

**Phase:** Construction · **Status:** Draft · **Owner:** _TBD_

## 1. Introduction
_Scope of testing and the documents it draws on ([SRS](../1-inception/requirements-srs.md),
[Use Case Model](../2-elaboration/use-case-model.md), [Architecture & Design](../2-elaboration/architecture-design.md))._

## 2. Test strategy

| Level | What it covers | Who | When |
|---|---|---|---|
| Unit | Individual functions and classes | Developer of the change | Every commit |
| Integration | Components and external interfaces | Test lead | Every iteration |
| System | End-to-end use cases | Whole team | End of each iteration |
| Acceptance | Sponsor's acceptance criteria | Sponsor + team | Transition |
| Regression | Previously passing cases | Automated where possible | Every release |

Non-functional testing: performance/load, security, usability, and recovery — each tied to
an NFR in the SRS.

## 3. Test environment
_Hardware, software, test data, accounts, and how to reset the environment between runs._

## 4. Entry and exit criteria

**Entry:** _feature merged, environment available, test data loaded._
**Exit:** _all Must-priority cases pass; no open critical or high defects; results recorded below._

## 5. Test cases

| ID | Requirement | Use case | Preconditions | Steps | Expected result | Priority |
|---|---|---|---|---|---|---|
| TC-01 | FR-01 | UC-01 | _TBD_ | _TBD_ | _TBD_ | Must |
| TC-02 | | | | | | |

## 6. Traceability matrix

| Requirement | Test cases | Status |
|---|---|---|
| FR-01 | TC-01 | Not run |
| NFR-01 | | Not run |

## 7. Defect management
Defects are filed as GitHub issues labeled `bug`, with severity
(`critical` / `high` / `medium` / `low`), steps to reproduce, and the test case that found
them. They enter the Kanban board like any other work.

## 8. Test results log

| Date | Build / commit | Cases run | Passed | Failed | Notes |
|---|---|---|---|---|---|
| _TBD_ | | | | | |

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft |
