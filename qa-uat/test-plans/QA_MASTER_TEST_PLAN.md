# QA master test plan

**Version:** 1.0  
**Authority:** `docs/SPEC.md`, DHS 837 Encounter Companion Guide  
**Scope:** Black-box functional QA of CLI (primary) and UI (spot checks)

## Objectives

1. Verify each SPEC capability end-to-end with manufactured data.
2. Confirm validation layers behave per requirements (not per implementation).
3. Confirm 999/835E generators produce structurally valid outputs.
4. Document gaps vs DHS MN–ITS per `docs/QA_VS_DHS_TEST.md`.

## In scope

| Area | Test case prefix |
|------|------------------|
| Generation + reproducibility | TC-QA-001–010 |
| Layer 1 envelope | TC-QA-011–015 |
| Layer 2 syntax | TC-QA-016–020 |
| Layer 3 DHS rules | TC-QA-021–035 |
| Layer 4 consistency | TC-QA-036–040 |
| 999 / 835E | TC-QA-041–045 |
| Negative / error fixtures | TC-QA-046–050 |

## Out of scope

- DHS production or MN–ITS test enrollment
- Provider/member eligibility databases
- Performance / load testing

## Entry criteria

- Toolkit installed (`pip install -e ".[ui]"`)
- Companion guide PDF present under `docs/reference/`
- `qa-uat/test-data/manifest.yaml` updated for new fixtures

## Exit criteria

- All P1 cases executed with recorded results
- Failures logged with companion-guide citation and reproduction steps
- Execution report in `qa-uat/reports/`

## Priority

| Priority | Meaning |
|----------|---------|
| P1 | Release blocker — clean path + critical DHS rules |
| P2 | Important edge cases |
| P3 | Simulation modes, program variants |

## Execution log

Update `registry/TEST_CASE_INDEX.md` after each run.
