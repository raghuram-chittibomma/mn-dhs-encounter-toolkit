# TC-UAT-008 — Pre-submission gate sign-off

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO QA lead |
| **Priority** | P1 |
| **Workflow** | Release gate |

## Objective

Confirm batch meets pre-submission gate: Layers 1–3 clean (Layer 4 per policy).

## Test data

Manufacture fresh clean mixed batch (seed 100).

## Steps

1. CLI: `mn-encounter validate --in <file> --layers 1,2,3 --format json --out qa-uat/results/executions/TC-UAT-008_gate.json`
2. Exit code must be 0
3. Complete `reports/templates/uat_signoff_report.md` with:
   - Cases executed
   - Known limitations vs DHS MN–ITS
   - Recommendation: proceed to DHS test / hold

## Expected results

| Check | Expected |
|-------|----------|
| L1–L3 | Zero errors |
| Sign-off doc | Filled template in `qa-uat/reports/` |

## Pass / fail

- **Pass:** Gate clean; sign-off documents residual DHS-test need.
- **Fail:** Layer 3 errors on clean scenario.
