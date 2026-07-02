# Test data manufacturing

All inputs live under `qa-uat/test-data/inputs/`. Register every file in
`manifest.yaml`.

## Method A — CLI generate (preferred)

```bash
mn-encounter list-scenarios
mn-encounter generate --scenario clean_professional_original --seed 42 \
  --out qa-uat/test-data/inputs/qa_clean_837p_seed42.x12
```

Combine scenarios for mixed batches:

```bash
mn-encounter generate \
  --scenario clean_professional_original \
  --scenario clean_institutional_original \
  --seed 42 \
  --out qa-uat/test-data/inputs/qa_clean_mixed_seed42.x12
```

## Method B — Error fixtures

```bash
mn-encounter generate --scenario err_missing_umpi --seed 42 \
  --out qa-uat/test-data/inputs/qa_err_missing_umpi_seed42.x12
```

`err_*` scenarios intentionally violate rules per SPEC.

## Method C — Guide-driven edits

1. Generate a clean file.
2. Remove or alter a segment required by the companion guide (document the edit).
3. Save as new filename; add manifest entry `manufactured_by: manual_edit`.

Example edits for planning:

| Intent | Edit |
|--------|------|
| Missing billing UMPI | Remove `REF*G2` in billing provider loop |
| Bad envelope | Mismatch ISA13 vs IEA02 |
| Void without ICN | Remove `REF*F8` on void claim |

## Method D — UI Scenario lab

Use Scenario lab page: pick scenario + seed → download → save to `inputs/`.

## Reproducibility

Record `--seed` and `--scenario` in the test case and manifest. Re-run must
produce byte-identical output for the same generator version.

## Synthetic data rules

- Fictional names and IDs only
- MN-style geography acceptable (cities/ZIPs)
- No production ISA06 or member identifiers
