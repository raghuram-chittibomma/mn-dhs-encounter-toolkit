# TC-UAT-001 — Analyst validates clean submission batch

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO encounter analyst |
| **Priority** | P1 |
| **Workflow** | Pre-submission validation |

## Objective

Analyst uploads a clean 837P+837I batch in the web UI and confirms readiness.

## Test data

Manufacture `QA-CLEAN-MIXED-42` (see TC-QA-001).

## Steps

1. Start `mn-encounter-ui` → http://localhost:8501
2. Open **Validate 837**
3. Upload `qa_clean_mixed_seed42.x12`
4. Review findings grouped by claim; confirm zero errors
5. Export JSON report; save to `qa-uat/results/executions/TC-UAT-001_ui.json`
6. Read sidebar privacy caption (local processing, no network transfer)

## Expected results

| Check | Expected |
|-------|----------|
| UI errors | None |
| Export | JSON downloadable |
| Privacy message | States local/in-memory processing |

## Pass / fail

- **Pass:** Analyst sees clean report and can export evidence.
- **Fail:** Unexpected errors or export failure.
