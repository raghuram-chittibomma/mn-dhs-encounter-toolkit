# Layer 3 gap resolution — 837I paid/allowed REF qualifiers (Phase 1)

Companion-guide cross-check (2026-07) identified that 837I uses **different**
REF qualifiers at claim level (loop 2300) vs service-line level (loop 2400).

## Guide mapping (dual-path)

| Level | Loop | Allowed | Paid | Guide pages |
|-------|------|---------|------|-------------|
| Claim total (inpatient) | 2300 | `REF*9A` | `REF*9C` | 837I p.43–44 |
| Service line (outpatient) | 2400 | `REF*9B` | `REF*9D` | 837I p.59 |

837P uses only the line-level pair (`REF*9B` / `REF*9D`, p.28).

## Toolkit resolution

1. **Writer** emits `REF*9B`/`REF*9D` at 2400 for both 837P and 837I line
   amounts. For 837I, optional `InstitutionalDetail.mco_paid_amount_claim` /
   `allowed_amount_claim` emit `REF*9C`/`REF*9A` in loop 2300 (before the
   first `LX`).
2. **Validator** — `L3-LINE-PAID-AMOUNT-REQUIRED-837I` passes when **either**
   path is present: at least one line-level `REF*9D`, **or** claim-header
   `REF*9C` (segments before the first `LX`).
3. **Validator** — `L3-837I-AMOUNT-REF-PLACEMENT` errors when `9A`/`9C`
   appear inside an `LX` group or `9B`/`9D` appear in the claim header.

## Phase 2 — 837I structural presence (2026-07)

| Rule | Guide requirement |
|------|-------------------|
| `L3-837I-CL1-REQUIRED` | CL1 segment present (p.43, REQ=Y) |
| `L3-837I-STATEMENT-DATES-REQUIRED` | DTP*434 present (p.42, REQ=Y) |

CL102 (admission source) is C1 in the guide — presence of the CL1 segment is
validated; individual CL1 element values are not enforced beyond writer defaults.

## Phase 3 — Demographics, attending UMPI, patient account (2026-07)

| Rule | Guide requirement |
|------|-------------------|
| `L3-SUBSCRIBER-DMG-REQUIRED` | DMG in 2010BA; DMG01=D8; DMG03 ∈ {M,F,U} (p.16/p.40) |
| `L3-837I-ATTENDING-UMPI-REQUIRED` | NM1*71 loop requires REF*G2 when present (p.51, C2) |
| `L3-837I-NTE-PATIENT-ACCOUNT-REQUIRED` | NTE*UPI with PAC= on all 837I (p.44, C2) |

Writer/generator emit attending physician (NM1*71), NTE*UPI, and patient account
on institutional scenarios.

## Phase 4 — Service facility UMPI + citation hygiene (2026-07)

| Item | Resolution |
|------|------------|
| `L3-SERVICE-FACILITY-UMPI-REQUIRED` | NM1*77 requires REF*G2 when loop present (p.22/p.52, C1) |
| `L3-BILLING-UMPI-REQUIRED` citation | 837P page corrected to p.17 (was p.16) |

Companion-guide cross-check gaps from the original report are addressed through
Phase 4. Institutional scenarios also emit service facility (NM1*77).
