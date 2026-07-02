# TC-QA-011 — Envelope control number mismatch detected

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC Layer 1 — ISA/IEA control number pairs must match |
| **Priority** | P1 |
| **Capability** | Validate Layer 1 |
| **SPEC reference** | Layer 1 — ISA/IEA control match |
| **Guide reference** | Envelope section — one interchange per file |

## Objective

Verify Layer 1 detects ISA13 ≠ IEA02 (envelope integrity).

## Test data

```bash
mn-encounter generate --scenario err_bad_envelope --seed 42 \
  --out qa-uat/test-data/inputs/qa_err_bad_envelope_seed42.x12
```

## Steps

1. `mn-encounter validate --in qa-uat/test-data/inputs/qa_err_bad_envelope_seed42.x12 --layers 1 --format json --out qa-uat/results/executions/TC-QA-011_validate.json`
2. Record exit code and findings.

## Expected results

| Check | Expected |
|-------|----------|
| Exit code | `1` |
| Layer | 1 |
| Finding theme | ISA13 ≠ IEA02 control number mismatch (SPEC Layer 1 envelope integrity) |

## Pass / fail

- **Pass:** Error-level Layer 1 finding on envelope control mismatch.
- **Fail:** Exit 0 or no envelope-related error.
