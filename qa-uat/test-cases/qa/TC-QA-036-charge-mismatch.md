# TC-QA-036 — Charge total mismatch fails Layer 4

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC Layer 4 — CLM02 total charge equals sum of service line charges; `err_charge_mismatch` scenario |
| **Priority** | P2 |
| **Capability** | Validate Layer 4 |
| **SPEC reference** | `err_charge_mismatch` |
| **Guide reference** | N/A (internal consistency per SPEC Layer 4) |

## Objective

Layer 4 detects CLM02 ≠ sum of line charges.

## Test data

```bash
mn-encounter generate --scenario err_charge_mismatch --seed 42 \
  --out qa-uat/test-data/inputs/qa_err_charge_mismatch_seed42.x12
```

## Steps

1. `mn-encounter validate --in <file> --layers 4 --format json --out qa-uat/results/executions/TC-QA-036_validate.json`

## Expected results

| Check | Expected |
|-------|----------|
| Exit code | `1` |
| Layer | 4 |
| Theme | Claim charge total inconsistent with service lines |

## Pass / fail

- **Pass:** Layer 4 error on charge mismatch.
- **Fail:** Exit 0 on Layer 4-only run.
