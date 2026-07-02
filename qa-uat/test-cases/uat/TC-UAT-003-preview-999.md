# TC-UAT-003 — Analyst previews 999 acknowledgment

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO encounter analyst |
| **Priority** | P2 |
| **Workflow** | Response preview |

## Objective

Analyst generates deterministic 999 from submission file via UI.

## Test data

`QA-CLEAN-MIXED-42`

## Steps

1. **Generate 999** page — upload clean 837
2. Select deterministic mode (default)
3. Download 999 file to `qa-uat/test-data/inputs/`
4. Optionally validate 999 via CLI `--layers 1`

## Expected results

| Check | Expected |
|-------|----------|
| Download | 999 `.x12` received |
| Analyst understanding | Acknowledgment is local preview, not DHS response (per QA_VS_DHS_TEST) |

## Pass / fail

- **Pass:** 999 downloaded successfully.
- **Fail:** UI error or empty file.

## UAT note

Record in sign-off that deterministic 999 does not reflect Layer 3 DHS rejections.
