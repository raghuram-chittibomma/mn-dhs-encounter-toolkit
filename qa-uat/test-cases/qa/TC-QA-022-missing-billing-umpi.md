# TC-QA-022 — Missing billing provider UMPI fails Layer 3

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC `err_missing_umpi`; guide L2010AA REF*G2 billing provider secondary identifier (DHS UMPI) |
| **Priority** | P1 |
| **Capability** | Validate Layer 3 |
| **SPEC reference** | `err_missing_umpi` scenario; UMPI in provider loops |
| **Guide reference** | Loop 2010AA — REF*G2 billing provider secondary identifier (UMPI) |

## Objective

Confirm validation rejects an encounter missing billing provider UMPI per companion guide.

## Test data

```bash
mn-encounter generate --scenario err_missing_umpi --seed 42 \
  --out qa-uat/test-data/inputs/qa_err_missing_umpi_seed42.x12
```

## Steps

1. Validate full layers: `mn-encounter validate --in qa-uat/test-data/inputs/qa_err_missing_umpi_seed42.x12 --format json --out qa-uat/results/executions/TC-QA-022_validate.json`
2. Confirm finding describes missing billing provider UMPI per guide (wording as emitted).
3. If JSON includes `source_citation`, record it — do not require a specific rule ID.

## Expected results

| Check | Expected |
|-------|----------|
| Exit code | `1` |
| Layer | 3 |
| Business condition | Billing provider missing REF*G2 (UMPI) — guide p.41: L2010AA billing provider secondary identification, qualifier G2, REF02 = DHS UMPI number (Req C1) |

## Pass / fail

- **Pass:** At least one Layer 3 error on missing billing UMPI theme; exit 1.
- **Fail:** Exit 0.
