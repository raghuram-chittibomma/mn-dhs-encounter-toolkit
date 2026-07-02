# TC-QA-041 — Deterministic 999 from clean 837 passes Layer 1

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC Capability 3 — 999 AK1/AK2/AK9 trace to ISA/GS/ST; generated 999 must pass Layer 1 |
| **Priority** | P1 |
| **Capability** | gen999 |
| **SPEC reference** | 999 deterministic; AK traces to ISA/GS/ST |
| **Guide reference** | mucg_999_ta1.pdf (syntax) |

## Objective

End-to-end: clean 837 → 999 → validate envelope of 999.

## Test data

Use `QA-CLEAN-MIXED-42` input.

## Steps

1. `mn-encounter gen999 --in qa-uat/test-data/inputs/qa_clean_mixed_seed42.x12 --out qa-uat/test-data/inputs/qa_clean_mixed_999_seed42.x12`
2. `mn-encounter validate --in qa-uat/test-data/inputs/qa_clean_mixed_999_seed42.x12 --layers 1`
3. Optionally inspect AK1/AK9 segments reference input control numbers.

## Expected results

| Check | Expected |
|-------|----------|
| gen999 exit | `0` |
| 999 L1 validate | `0` |
| AK segments | Present; trace to submitted interchange |

## Pass / fail

- **Pass:** 999 generated and envelope-valid.
- **Fail:** Generation failure or 999 envelope errors.

## Note (scope)

Per `docs/QA_VS_DHS_TEST.md`, local deterministic 999 reflects L1–L2 only — not full DHS business-rule rejection.
