# Functional requirements summary (from SPEC)

Distilled for black-box QA/UAT. Full text: `docs/SPEC.md`.

## System under test

MN DHS **MCO encounter** toolkit (not fee-for-service billing):

- **In scope:** 837P, 837I, 999, 835E
- **Submitter:** MCO trading partner; **receiver:** Minnesota DHS (MN–ITS)
- **Runtime:** Python 3.11+, CLI + optional local web UI
- **Data:** Synthetic only — no real PII

## Capability 1 — Synthetic generation

Produces fictional MCOs, providers (NPI/UMPI/TIN), members, and encounters.

**Named scenarios (minimum):**

| Scenario | Intent |
|----------|--------|
| `clean_professional_original` | Valid 837P, MCO-paid amount, no TPL |
| `clean_institutional_original` | Valid 837I inpatient |
| `professional_with_tpl` | 837P with COB/TPL |
| `institutional_with_tpl` | 837I with TPL |
| `void_encounter` | CLM05-3=8 with original ICN |
| `replacement_encounter` | CLM05-3=7 with original ICN |
| `epsdt_teen_checkup` | EPSDT CRC values |
| `atypical_provider` | TIN primary, UMPI secondary G2 |
| `pmap_professional` / `minnesotacare_professional` / `msho_institutional` | Program variants |
| `zero_paid_encounter` | MCO paid $0 |
| `multi_provider` | Billing ≠ rendering |
| `err_*` scenarios | Intentional rule violations for negative testing |

Requirements: reproducible `--seed`, multi-encounter batches, configurable
separators/control numbers, refuse inconsistent non-error encounters.

## Capability 2 — Validation (four layers)

| Layer | Scope |
|-------|--------|
| 1 | Envelope: ISA/IEA, GS/GE, ST/SE, counts, separators |
| 2 | Base X12 TR3 syntax inside 837 |
| 3 | DHS encounter companion-guide business rules |
| 4 | Cross-field consistency (charges, pointers, void ICN, dates) |

**Output:** severity, location, description, layer; text or JSON; CI exit codes
(0 = no errors, 1 = errors, 2 = fatal).

## Capability 3 — Response generation

**999:** From 837; deterministic (reflects L1–L2 findings) or simulation (seeded random).

**835E:** From 837; deterministic (echo MCO-reported paid amounts) or simulation.

Named response scenarios: `accept_all`, `reject_missing_umpi`, `reject_bad_envelope`,
`partial_accept`, `void_confirmed`, `replacement_accepted`, `zero_pay_accepted`.

## Encounter concepts to test

- MCO vs provider identifiers (ISA06 vs inner loops)
- UMPI (REF*G2) in provider loops
- MCO-paid amounts (837P line level; 837I claim/line per guide)
- TPL / COB (up to 10 SBR)
- Void (8) and replacement (7) with ICN
- EPSDT CRC when applicable
- 835E as encounter remittance variant

## End-to-end flow

```
generate 837 → validate (L1–4) → gen999 / gen835e
```

Web UI exposes: Validate 837, Validation layers catalog, Generate 999/835E,
Scenario lab.
