# Test artifact provenance

## Bootstrap cases (developer-authored)

The initial files under `test-cases/`, `test-plans/`, `test-data/manifest.yaml`,
and `authoritative-context/REQUIREMENTS_SUMMARY.md` were created in the
**implementation chat window**, not by an isolated QA agent.

### Context used during bootstrap (not independent)

| Source | Used? |
|--------|-------|
| `docs/SPEC.md` | Yes |
| `docs/QA_VS_DHS_TEST.md` | Yes |
| `docs/reference/dhs_837_encounter_companion_guide.pdf` | Partially |
| `README.md` → `BLACK_BOX_INTERFACE.md` | Yes |
| `docs/VALIDATION_LAYERS.md` | Yes (should not have been) |
| This conversation / Phases 1–4 implementation work | Yes |
| `src/**`, `tests/**` | No direct reads |

### Known contamination

- **TC-QA-023** originally listed specific 837I segments informed by
  implementation work; scrubbed to require guide-derived checklist at execution.
- **Negative case selection** (`err_missing_umpi`, etc.) — scenario names are
  in SPEC, but which negatives to include was influenced by what was built here.
- **`BLACK_BOX_INTERFACE.md`** — execution surface only; do not use to *plan*
  expected validator behavior.

### What is still trustworthy

- Folder layout and templates
- Isolation rules in `AGENTS.md` and `.cursor/skills/`
- SPEC-named scenarios as *inputs* (verify via `list-scenarios` at run time)
- Exit-code semantics documented in SPEC / black-box interface

## Required review before sign-off

In a **new chat** with `mn-dhs-qa-agent` or `mn-dhs-uat-agent`:

1. Read this file.
2. For each case tagged **Bootstrap — review required**:
   - Re-derive expected results from SPEC + companion guide PDF only.
   - Replace or approve the case; set `review_status: approved` in the case header.
3. Add new cases for guide requirements not covered.
4. Record review in `registry/TEST_CASE_INDEX.md` (column: Review).

Until review is complete, treat bootstrap cases as **scaffold**, not signed-off
test design.

## After review

When a case is approved, remove the bootstrap banner and update this file's
case list under **Reviewed and approved**.

## Reviewed and approved (2026-07-02)

Independent mn-dhs-qa-agent session: expectations re-derived from
`docs/SPEC.md` and `docs/reference/dhs_837_encounter_companion_guide.pdf`
only. All nine QA bootstrap cases executed in `qa-uat/`; report:
`qa-uat/reports/qa_execution_2026-07-02.md`.

| Case | Review | Execution |
|------|--------|-----------|
| TC-QA-001 | approved | pass |
| TC-QA-011 | approved | pass |
| TC-QA-022 | approved | pass |
| TC-QA-023 | approved | pass (+ guide checklist) |
| TC-QA-028 | approved | pass |
| TC-QA-030 | approved | pass |
| TC-QA-036 | approved | pass |
| TC-QA-041 | approved | pass |
| TC-QA-042 | approved | pass |

UAT bootstrap review and execution completed 2026-07-02; see **Reviewed and approved — UAT** below.

## Reviewed and approved — UAT (2026-07-02)

Independent mn-dhs-uat-agent session: expectations re-derived from
`docs/SPEC.md`, `docs/QA_VS_DHS_TEST.md`, and companion guide PDF.
Executed TC-UAT-001 through TC-UAT-008 via web UI at http://localhost:8501
(plus CLI gate for TC-UAT-008). Report: `qa-uat/reports/uat_signoff_2026-07-02.md`.

| Case | Review | Execution |
|------|--------|-----------|
| TC-UAT-001 | approved | pass (JSON export gap on clean runs — see sign-off) |
| TC-UAT-002 | approved | pass |
| TC-UAT-003 | approved | pass |
| TC-UAT-004 | approved | pass |
| TC-UAT-005 | approved | pass |
| TC-UAT-006 | approved | pass |
| TC-UAT-007 | approved | pass |
| TC-UAT-008 | approved | pass |
