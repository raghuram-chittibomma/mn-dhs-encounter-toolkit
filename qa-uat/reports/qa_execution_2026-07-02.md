# QA execution report

**Run ID:** RUN-20260702-01  
**Executor:** mn-dhs-qa-agent (black-box)  
**Date:** 2026-07-02  
**Authority:** `docs/SPEC.md` + `docs/reference/dhs_837_encounter_companion_guide.pdf` only

## Summary

| Metric | Count |
|--------|-------|
| Cases planned | 9 |
| Executed | 9 |
| Passed | 9 |
| Failed | 0 |
| Blocked | 0 |

## Environment

- OS: Windows 10 (win32 10.0.26200)
- Python: 3.14 (project venv)
- Install: `pip install -e .` (CLI used; UI not exercised)

## Results

| Case ID | Priority | Status | Notes |
|---------|----------|--------|-------|
| TC-QA-001 | P1 | pass | Exit 0, 0 errors; generator deterministic (two fresh generates matched); stored fixture predates current generator bytes |
| TC-QA-011 | P1 | pass | Exit 1; L1 ISA13≠IEA02 — `TC-QA-011_validate.json` |
| TC-QA-022 | P1 | pass | Exit 1; L3 missing billing REF*G2 UMPI — guide p.41 — `TC-QA-022_validate.json` |
| TC-QA-023 | P1 | pass | Exit 0; guide checklist `TC-QA-023_checklist.md` |
| TC-QA-028 | P2 | pass | Exit 0; SBR*P + Medicare payer NM1 present |
| TC-QA-030 | P1 | pass | Exit 0; CLM05-3=8 + REF*F8 ICN per guide p.43 |
| TC-QA-036 | P2 | pass | Exit 1; L4 CLM02 ≠ line sum — `TC-QA-036_validate.json` |
| TC-QA-041 | P1 | pass | gen999 exit 0; 999 L1 exit 0; AK1/AK2/AK9 present |
| TC-QA-042 | P1 | pass | gen835e exit 0; 835E L1 exit 0; CLP/SVC/BPR/TRN present |

## Failures (detail)

None.

## Scope notes

Local validation and generated 999/835E are **not** DHS MN–ITS integration proof.
See `docs/QA_VS_DHS_TEST.md`. Deterministic 999 reflects L1–L2 only; 835E
deterministic echoes MCO-reported paid amounts from the 837.

## Sign-off

- [x] P1 cases complete
- [x] Failures triaged (none)

**QA lead:** mn-dhs-qa-agent  **Date:** 2026-07-02
