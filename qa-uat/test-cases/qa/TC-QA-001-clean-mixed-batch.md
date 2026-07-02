# TC-QA-001 — Clean mixed batch validates with zero errors

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC Capability 1 & 2 — `clean_professional_original` + `clean_institutional_original` must produce zero error-level findings |
| **Priority** | P1 |
| **Capability** | Generate + Validate |
| **SPEC reference** | Capability 1 & 2 — clean scenarios |
| **Guide reference** | DHS 837 Encounter Companion Guide (general compliance) |

## Objective

Confirm a reproducible 837P+837I batch passes all four validation layers.

## Test data

Manufacture per `manifest.yaml` → `QA-CLEAN-MIXED-42`:

```bash
mn-encounter generate \
  --scenario clean_professional_original \
  --scenario clean_institutional_original \
  --seed 42 \
  --out qa-uat/test-data/inputs/qa_clean_mixed_seed42.x12
```

## Steps

1. Run `mn-encounter validate --in qa-uat/test-data/inputs/qa_clean_mixed_seed42.x12 --format json --out qa-uat/results/executions/TC-QA-001_validate.json`
2. Note exit code.
3. Re-run generate with same flags; compare file hash to confirm reproducibility.

## Expected results

| Check | Expected | Guide / SPEC basis |
|-------|----------|-------------------|
| Exit code | `0` | SPEC Capability 2 — CI exit 0 = no errors |
| Error-level findings | `0` | SPEC test requirements — clean scenarios assert zero errors |
| Layers run | 1, 2, 3, 4 (default) | SPEC four validation layers |
| Reproducibility | Two consecutive `generate` calls with same scenario+seed produce identical bytes | SPEC Capability 1 — seedable reproducible scenarios |

## Pass / fail

- **Pass:** Exit 0, zero errors, reproducible output.
- **Fail:** Any error finding or non-reproducible generate.
