# UI screenshots

Portfolio images captured **after real interactions** (not empty page loads).

| File | Interaction |
|------|-------------|
| `validate_837_error_finding.png` | Upload `examples/err_missing_umpi.x12` → 1 error, claim table, findings |
| `validation_layers_umpi_search.png` | Search `UMPI` → filtered rule table |
| `scenario_lab_batch_generated.png` | Select `clean_professional_original`, generate batch → download ready |
| `generate_999_preview.png` | Upload `examples/clean_batch.x12`, deterministic 999 → preview + download |

GitHub caches README images by path — if thumbnails look stale after an update, rename files or change README paths.

## Regenerate

```bash
pip install playwright && playwright install chromium
pip install -e ".[ui]"
mn-encounter-ui   # in another terminal
python scripts/capture_portfolio_screenshots.py
```
