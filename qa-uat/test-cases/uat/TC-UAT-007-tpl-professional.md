# TC-UAT-007 — Analyst handles TPL professional encounter

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO encounter analyst |
| **Priority** | P2 |
| **Workflow** | TPL / COB validation |

## Objective

Analyst validates a professional encounter with third-party liability (COB) loops.

## Test data

`QA-TPL-42` (see TC-QA-028).

## Steps

1. **Validate 837** — upload `qa_professional_tpl_seed42.x12`
2. Confirm zero errors
3. Review claim for COB / other-subscriber context

## Expected results

| Check | Expected |
|-------|----------|
| UI errors | None |
| TPL context | Non-Medicaid payer COB structure (e.g. SBR*P) present |

## Pass / fail

- **Pass:** Clean validation on TPL scenario.
- **Fail:** Errors or inability to review TPL claim.
