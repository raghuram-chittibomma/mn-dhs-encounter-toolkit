# TC-UAT-002 — Analyst remediates missing UMPI finding

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO encounter analyst |
| **Priority** | P1 |
| **Workflow** | Error remediation |

## Objective

Analyst identifies billing UMPI violation from validation report and understands fix.

## Test data

`QA-ERR-UMPI-42` (see TC-QA-022).

## Steps

1. **Validate 837** — upload `qa_err_missing_umpi_seed42.x12`
2. Locate finding describing missing billing provider UMPI / REF*G2
3. Note companion guide citation in finding if shown
4. Optional: **Validation layers** — reference only at execution; do not use to
   pre-write expected rule IDs.
5. Document analyst action: add billing UMPI per companion guide (remediation simulated — note in report)

## Expected results

| Check | Expected |
|-------|----------|
| Error visible | At least one error on billing UMPI |
| Citation | Companion guide page referenced in UI or JSON |
| Analyst outcome | Clear which loop/segment to fix |

## Pass / fail

- **Pass:** Actionable error with guide citation.
- **Fail:** No error on bad file or unclear message.
