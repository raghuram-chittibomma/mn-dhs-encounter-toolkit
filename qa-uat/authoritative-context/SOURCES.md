# Authoritative sources for QA / UAT agents

Read **only** these documents when planning expected behavior.

## Primary

| Document | Path | Use for |
|----------|------|---------|
| Project specification | `docs/SPEC.md` | Capabilities, named scenarios, validation layers, 999/835E requirements |
| DHS 837 Encounter Companion Guide | `docs/reference/dhs_837_encounter_companion_guide.pdf` | Layer 3 business rules, segment requirements, MCO encounter specifics |
| QA scope vs DHS test | `docs/QA_VS_DHS_TEST.md` | What local testing can and cannot prove |

## Secondary (response / envelope)

| Document | Path | Use for |
|----------|------|---------|
| AUC MUCG 999/TA1 | `docs/reference/mucg_999_ta1.pdf` | 999/TA1 syntax expectations |
| AUC MUCG 835 | `docs/reference/mucg_835.pdf` | Base 835 structure for 835E checks |
| Document index | `docs/reference/DOCUMENT_INDEX.md` | Which PDF applies to which transaction |

## Requirements digest

| Document | Path |
|----------|------|
| Condensed functional requirements | `qa-uat/authoritative-context/REQUIREMENTS_SUMMARY.md` |

## Black-box execution

| Document | Path |
|----------|------|
| CLI and UI surface | `qa-uat/BLACK_BOX_INTERFACE.md` |

## Do not use for test design

- `src/**`, `tests/**`, `docs/VALIDATION_LAYERS.md`, `docs/RULE_SOURCE_TRACE.md`
- `KNOWN_LIMITATIONS.md` (implementation gaps — use only if user explicitly asks for scope discussion)
