# UAT master test plan

**Version:** 1.0  
**Persona:** MCO encounter data analyst preparing MN–ITS submission  
**Authority:** `docs/SPEC.md`, companion guide, `docs/QA_VS_DHS_TEST.md`

## Objectives

1. Validate real-world workflows: build batch → validate → remediate → preview responses.
2. Confirm web UI supports analyst tasks without CLI expertise.
3. Confirm privacy messaging and local-only processing meet MCO expectations.
4. Produce UAT sign-off report for stakeholder review.

## Scenarios

| ID | Workflow |
|----|----------|
| TC-UAT-001 | First-time analyst validates a clean 837P+837I batch |
| TC-UAT-002 | Analyst fixes UMPI error using validation report |
| TC-UAT-003 | Analyst previews 999 before submission |
| TC-UAT-004 | Analyst previews 835E remittance echo |
| TC-UAT-005 | Analyst uses Scenario lab for training/demo |
| TC-UAT-006 | Analyst validates void encounter with ICN |
| TC-UAT-007 | Analyst handles TPL professional encounter |
| TC-UAT-008 | Sign-off: pre-submission gate (L1–3 clean) |

## Success criteria

- Analyst completes each workflow without reading source code
- Findings cite companion guide in UI where applicable
- Exported JSON suitable for ticket attachment
- UAT sign-off documents known limitations vs DHS test

## Out of scope

- Production MN–ITS upload
- Cross-MCO trading partner onboarding

## Deliverables

- Completed cases under `qa-uat/test-cases/uat/`
- `reports/uat_signoff_<date>.md` from template
