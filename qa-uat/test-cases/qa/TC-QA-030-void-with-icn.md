# TC-QA-030 — Void encounter carries original ICN

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC `void_encounter` CLM05-3=8; guide p.43 REF*F8 original ICN when frequency=8 void |
| **Priority** | P1 |
| **Capability** | Generate + Validate |
| **SPEC reference** | `void_encounter`; CLM05-3=8; REF*F8 |
| **Guide reference** | Void claims — REF*F8 with original MCO ICN |

## Objective

Void scenario validates clean and includes void frequency with ICN reference.

## Test data

```bash
mn-encounter generate --scenario void_encounter --seed 42 \
  --out qa-uat/test-data/inputs/qa_void_encounter_seed42.x12
```

## Steps

1. Validate full layers.
2. Per companion guide void section: confirm void frequency (CLM05-3=8 per SPEC)
   and original ICN reference segment(s) — cite guide page; do not assume REF*F8
   without verifying in PDF.

## Expected results

| Check | Expected |
|-------|----------|
| Exit code | `0` |
| Void ICN | CLM05-3=8 (void) and REF*F8 with MCO original claim ICN — guide p.43: "USED WHEN CLM05-3 IS 8-VOID" |

## Pass / fail

- **Pass:** Clean validation; void ICN reference present.
- **Fail:** Missing ICN or validation errors.
