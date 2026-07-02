# Example files

Committed samples for quick validation without running the generator.

| File | Description |
|------|-------------|
| `clean_batch.x12` | Two encounters (837P + 837I), seed 42 — passes all four validation layers. The 837I claim includes institutional segments (`NTE*UPI`, `NM1*71` attending, `NM1*77` service facility). |
| `clean_batch_validation.json` | JSON report for `clean_batch.x12` (0 findings) |
| `err_missing_umpi.x12` | Intentional Layer 3 error fixture — billing provider missing REF*G2 (UMPI) |
| `err_missing_umpi_validation.json` | JSON report showing `L3-BILLING-UMPI-REQUIRED` |

## Try it

```bash
pip install -e .
mn-encounter validate --in examples/clean_batch.x12
mn-encounter validate --in examples/err_missing_umpi.x12
mn-encounter validate --in examples/clean_batch.x12 --format json
```

`err_missing_umpi.x12` exits with code `1` (error-level finding) — expected for a negative test.
