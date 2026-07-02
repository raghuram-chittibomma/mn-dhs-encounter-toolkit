# TC-UAT-006 — Analyst validates void encounter with ICN

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO encounter analyst |
| **Priority** | P1 |
| **Workflow** | Void encounter validation |

## Objective

Analyst uploads a void-frequency encounter and confirms clean validation with original ICN reference.

## Test data

`QA-VOID-42` (see TC-QA-030).

## Steps

1. **Validate 837** — upload `qa_void_encounter_seed42.x12`
2. Confirm zero errors in summary metrics
3. Review claim context for void frequency and original ICN reference

## Expected results

| Check | Expected |
|-------|----------|
| UI errors | None |
| Void structure | Void frequency and REF*F8 original ICN present per companion guide |

## Pass / fail

- **Pass:** Clean validation; analyst can proceed with void submission prep.
- **Fail:** Unexpected errors on manufactured void scenario.
