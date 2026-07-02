# TC-UAT-004 — Analyst previews 835E remittance echo

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO encounter analyst |
| **Priority** | P2 |
| **Workflow** | Response preview |

## Objective

Analyst generates deterministic 835E from submission file via UI and understands it echoes MCO-reported amounts.

## Test data

`QA-CLEAN-MIXED-42`

## Steps

1. **Generate 835E** page — upload clean 837
2. Select deterministic mode (default)
3. Click **Generate 835E**, then **Download 835E file** to `qa-uat/test-data/inputs/`
4. Optionally validate 835E via CLI `--layers 1`

## Expected results

| Check | Expected |
|-------|----------|
| Download | 835E `.x12` received with CLP/SVC segments |
| Analyst understanding | Remittance is local echo, not DHS adjudication (per QA_VS_DHS_TEST) |

## Pass / fail

- **Pass:** 835E downloaded successfully with claim payment structure.
- **Fail:** UI error or empty file.
