# UI screenshots

Portfolio images captured **after real interactions** (not empty page loads).

| File | Interaction |
|------|-------------|
| `validate_837.png` | Upload `examples/err_missing_umpi.x12` → 1 error, claim table, findings |
| `validation_layers.png` | Search `UMPI` → filtered rule table (Layer 3 tab open) |
| `scenario_lab.png` | Select `clean_professional_original`, generate batch → download ready |
| `generate_999.png` | Upload `examples/clean_batch.x12`, deterministic 999 → preview + download |

## Regenerate

```bash
pip install playwright && playwright install chromium
pip install -e ".[ui]"
mn-encounter-ui   # in another terminal
python scripts/capture_portfolio_screenshots.py
```
