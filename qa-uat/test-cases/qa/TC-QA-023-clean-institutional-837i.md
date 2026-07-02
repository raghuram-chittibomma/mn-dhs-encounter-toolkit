# TC-QA-023 — Clean institutional 837I meets guide requirements

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC `clean_institutional_original`; guide 837I sections pp. 38–51 (CL1, DTP*434/435/096, NTE*UPI, NM1*71+REF*G2, line paid refs, AMT*GT) |
| **Priority** | P1 |
| **Capability** | Generate + Validate |
| **SPEC reference** | `clean_institutional_original` — valid 837I inpatient with MCO-paid amount |
| **Guide reference** | *Derive at review:* DHS 837 Encounter Companion Guide — 837I institutional sections (record page/loop citations in execution report) |

## Objective

Confirm a SPEC clean institutional scenario validates with zero errors, and
document which 837I segments the companion guide requires (checklist filled
during review/execution — not pre-filled from implementation knowledge).

## Planning step (before execution)

1. Read companion guide 837I institutional claim sections.
2. Build a **guide-derived checklist** (segment/loop, REQ column, page cite).
3. Save checklist in `qa-uat/results/executions/TC-QA-023_checklist.md`.
4. Do **not** copy segment lists from `VALIDATION_LAYERS.md`, code, or prior chats.

## Test data

```bash
mn-encounter list-scenarios   # confirm clean_institutional_original exists
mn-encounter generate --scenario clean_institutional_original --seed 42 \
  --out qa-uat/test-data/inputs/qa_clean_837i_seed42.x12
```

## Steps

1. Full validation → JSON to `results/executions/TC-QA-023_validate.json`.
2. Against your checklist only: note which required elements appear in the file.
3. Record any gaps between guide checklist and file content (informational).

## Expected results

| Check | Expected |
|-------|----------|
| Exit code | `0` (per SPEC clean scenario) |
| Error-level findings | `0` |
| Segment checklist | Completed from guide with citations — attached to run |

## Pass / fail

- **Pass:** Exit 0; checklist completed from guide; no unresolved guide REQ=Y gaps in file.
- **Fail:** Exit 1 on clean scenario, or checklist not guide-sourced.
