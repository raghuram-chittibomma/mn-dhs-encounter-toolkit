# UAT sign-off report

**Release / milestone:** MN DHS Encounter Toolkit v0.1 — internal pre-flight UAT  
**UAT lead:** mn-dhs-uat-agent  
**Date:** 2026-07-02  
**Persona validated:** MCO encounter data analyst

## UAT cases

| Case ID | Title | Status | Tester | Notes |
|---------|-------|--------|--------|-------|
| TC-UAT-001 | Clean batch validation | pass | mn-dhs-uat-agent | 0 errors; privacy caption confirmed; JSON export absent when zero findings (claims CSV only) |
| TC-UAT-002 | UMPI remediation | pass | mn-dhs-uat-agent | Actionable L3 billing UMPI error; guide p.17/p.40 cited; JSON exported |
| TC-UAT-003 | 999 preview | pass | mn-dhs-uat-agent | Deterministic 999 via UI; L1 envelope validate exit 0 |
| TC-UAT-004 | 835E preview | pass | mn-dhs-uat-agent | Deterministic 835E via UI; CLP/SVC present; L1 exit 0 |
| TC-UAT-005 | Scenario lab | pass | mn-dhs-uat-agent | `epsdt_teen_checkup` seed 99 UI-only generate → validate clean |
| TC-UAT-006 | Void with ICN | pass | mn-dhs-uat-agent | Void scenario 0 errors; REF*F8 / void frequency in file |
| TC-UAT-007 | TPL professional | pass | mn-dhs-uat-agent | TPL scenario 0 errors; SBR*P COB structure present |
| TC-UAT-008 | Pre-submission gate | pass | mn-dhs-uat-agent | Fresh seed-100 mixed batch L1–L3 exit 0 |

**Evidence:** `qa-uat/results/executions/TC-UAT-*_20260702T172018Z.json`, `TC-UAT-002_ui.json`, `TC-UAT-008_gate.json`, UI artifacts under `qa-uat/test-data/inputs/uat_*`.

## Business acceptance

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Analyst can validate without CLI | Yes | TC-UAT-001, 002, 006, 007 completed in web UI only |
| Errors cite companion guide where applicable | Yes | TC-UAT-002 shows `dhs_837_encounter_companion_guide.pdf p.17/p.40` |
| Local/privacy messaging clear | Yes | Sidebar: "processed in memory only—nothing is stored on disk or sent over the internet" |
| JSON export suitable for audit trail | Yes | JSON/CSV export on all runs including zero findings (fixed post-UAT 2026-07-02) |
| User understands local vs DHS test scope | Yes | 999/835E pages produce local preview; sign-off acknowledges QA_VS_DHS_TEST limits |

## Known limitations (acknowledged)

Per `docs/QA_VS_DHS_TEST.md`:

- [x] Team understands local 999 ≠ DHS business-rule rejection (deterministic 999 re-runs L1–L2 only)
- [x] Team understands 835E is local echo/simulation (deterministic mode echoes MCO-paid amounts from 837)
- [x] DHS MN–ITS test still required for integration sign-off

**Additional UAT observations**

- ~~JSON report download appears only after error-level findings~~ — fixed: JSON/CSV offered on clean runs too.
- Synthetic scenarios do not prove DHS enrollment, provider registry, or transport acceptance.

## Recommendation

- [x] **Accept** for internal pre-flight QA
- [ ] **Accept with conditions** (list):
  - ~~Add JSON export on clean validation runs~~ — addressed in UI (2026-07-02).
  - Proceed to DHS MN–ITS test for integration sign-off before production submission.
- [ ] **Reject** (list blockers):

**Signatures**

| Role | Name | Date |
|------|------|------|
| UAT lead | mn-dhs-uat-agent | 2026-07-02 |
| Business owner | _(pending stakeholder review)_ | |
