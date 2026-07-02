# TC-QA-042 — Deterministic 835E echoes MCO-paid amounts

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC Capability 3 — 835E deterministic echoes MCO-paid amounts; output passes Layer 1 envelope |
| **Priority** | P1 |
| **Capability** | gen835e |
| **SPEC reference** | 835E deterministic echoes 837 paid amounts |
| **Guide reference** | mucg_835.pdf (base 835 structure); encounter-specific remarks per SPEC |

## Objective

Clean 837 → 835E → 835E passes Layer 1 envelope.

## Test data

Use `QA-CLEAN-MIXED-42`.

## Steps

1. `mn-encounter gen835e --in qa-uat/test-data/inputs/qa_clean_mixed_seed42.x12 --mode deterministic --out qa-uat/test-data/inputs/qa_clean_mixed_835e_seed42.x12`
2. `mn-encounter validate --in qa-uat/test-data/inputs/qa_clean_mixed_835e_seed42.x12 --layers 1`
3. Confirm CLP/SVC segments present (black-box text search).

## Expected results

| Check | Expected |
|-------|----------|
| gen835e exit | `0` |
| 835E L1 | `0` |
| Content | CLP and SVC segments present |

## Pass / fail

- **Pass:** 835E generated with claim/service payment structure.
- **Fail:** Generation or envelope failure.
