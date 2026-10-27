# UI screenshots

Portfolio images captured **after real interactions** (not empty page loads).

| File | Interaction |
|------|-------------|
| `edi_file_annotated_error.png` | Upload `examples/err_missing_umpi.x12` on **EDI file** → findings plus the annotated outline with the error still colored |
| `validation_layers_enabled_rules.png` | Layer 3 rule table with **Enabled** checkboxes (all rules on until one is unchecked) |
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
