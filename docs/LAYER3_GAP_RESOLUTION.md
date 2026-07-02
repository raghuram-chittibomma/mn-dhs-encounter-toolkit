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

Remaining cross-check gaps (CL1, DMG, NTE*UPI, etc.) are tracked for Phase 2+.
