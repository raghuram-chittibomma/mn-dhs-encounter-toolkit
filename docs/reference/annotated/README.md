# Annotated DHS 837 Encounter Companion Guide

| File | Description |
|------|-------------|
| [`dhs_837_encounter_companion_guide_annotated.pdf`](dhs_837_encounter_companion_guide_annotated.pdf) | Highlighted copy of the primary authority PDF |

## How to read highlights

- **Yellow highlights** mark passages used to implement **Layer 1** and **Layer 3** validation rules.
- Hover or click a highlight in most PDF viewers to see the **rule ID** (e.g. `L3-BILLING-UMPI-REQUIRED`) and the source citation text.
- The pristine source PDF remains at [`../dhs_837_encounter_companion_guide.pdf`](../dhs_837_encounter_companion_guide.pdf).

## Regenerate

```bash
pip install pymupdf
python scripts/annotate_dhs_companion_pdf.py
```

Full rule-to-source table (no PDF required): [`../../RULE_SOURCE_TRACE.md`](../../RULE_SOURCE_TRACE.md).
