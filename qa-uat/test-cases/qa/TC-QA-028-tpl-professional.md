# TC-QA-028 — TPL professional encounter includes COB loops

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Reviewed by** | mn-dhs-qa-agent |
| **Review date** | 2026-07-02 |
| **Authority** | SPEC `professional_with_tpl`; guide L2320 other subscriber / COB when member has other insurance (pp. 3, 53–55) |
| **Priority** | P2 |
| **Capability** | Generate + Validate |
| **SPEC reference** | `professional_with_tpl`; TPL COB up to 10 SBR |
| **Guide reference** | Loop 2320 / COB — TPL payer when member has other insurance |

## Objective

Manufactured TPL encounter validates clean and contains COB-related structure.

## Test data

```bash
mn-encounter generate --scenario professional_with_tpl --seed 42 \
  --out qa-uat/test-data/inputs/qa_professional_tpl_seed42.x12
```

## Steps

1. Validate: exit code and error count.
2. Inspect file text: confirm COB/TPL structure per **your companion guide read**
   (document which loops/segments you checked and page cites).

## Expected results

| Check | Expected |
|-------|----------|
| Exit code | `0` |
| TPL structure | SBR loop with non-Medicaid payer (e.g. SBR01=P, SBR09=MB) and COB adjudication amounts present — guide L2320 required when TPL/MCO adjudication submitted |

## Pass / fail

- **Pass:** Zero errors; TPL loops present.
- **Fail:** Errors or absent TPL structure.
