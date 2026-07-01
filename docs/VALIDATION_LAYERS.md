# Validation layers reference

The toolkit runs up to **four independent layers** against each 837P/837I file.
Layers can be selected individually on the CLI (`--layers 1,2,3,4`) or in the
web UI checkboxes. Each layer returns **findings** with a `rule_id`, severity,
and (when available) line number and source citation.

In the **web UI**, open **Validation layers** in the sidebar menu for a searchable
rule catalog (same content as this document).

**QA scope:** see [`QA_VS_DHS_TEST.md`](QA_VS_DHS_TEST.md) for what this toolkit
can prove vs. submitting to DHS MN–ITS test.

| Layer | Scope | Authority | Typical examples |
|-------|--------|-----------|------------------|
| **1** | Interchange / functional-group / transaction-set **envelope** | Base X12 + one DHS rule | ISA/IEA control numbers, GS/GE pairing, SE segment counts |
| **2** | **Base X12 / TR3 syntax** inside the 837 | X12 005010X222A1 / X223A2 (not DHS-specific) | Money/date formats, NPI Luhn, required BHT/LX/HI |
| **3** | **MN DHS encounter business rules** | `dhs_837_encounter_companion_guide.pdf` | UMPI, MCO-paid amounts, payer identity, EPSDT |
| **4** | **Cross-field consistency** on parsed claim data | Toolkit internal invariants | Charge totals, diagnosis pointers, void ICN |

**999 deterministic mode** re-runs **Layers 1 and 2 only** (envelope + syntax scope of a 999).

---

## Layer 1 — Envelope integrity

**Module:** `validator/layer1_envelope.py`

| Rule ID | What it checks |
|---------|----------------|
| `L1-ISA-PRESENT` | ISA segment exists |
| `L1-IEA-PRESENT` | IEA segment exists |
| `L1-ONE-ISA-PER-FILE` | Exactly one ISA per file (DHS requirement) |
| `L1-ISA-IEA-CONTROL-MATCH` | ISA13 = IEA02 |
| `L1-ISA13-FORMAT` | ISA13 is 9 digits, not all zeros |
| `L1-IEA-GROUP-COUNT` | IEA01 = actual GS count |
| `L1-GS-GE-CONTROL-MATCH` | Each GS06 = paired GE02 |
| `L1-GE-ST-COUNT` | GE01 = ST count within the group |
| `L1-ST-SE-CONTROL-MATCH` | Each ST02 = paired SE02 |
| `L1-SE-SEGMENT-COUNT` | SE01 = segment count ST..SE inclusive |
| `L1-SEPARATORS-DISTINCT` | Four delimiters are distinct single characters |

---

## Layer 2 — Base X12 / TR3 syntax

**Module:** `validator/layer2_syntax.py`  
**Note:** These are base implementation-guide rules, not DHS encounter business rules. No per-rule `SOURCE:` line in output.

| Rule ID | What it checks |
|---------|----------------|
| `L2-ST01-VALUE` | ST01 = `837` |
| `L2-BHT-PRESENT` | At least one BHT per transaction set |
| `L2-CLM-EXACTLY-ONE-PER-CLAIM` | Exactly one CLM per claim block |
| `L2-CLM02-MONEY-FORMAT` | CLM02 is non-negative `NNN.NN` |
| `L2-AMT02-MONEY-FORMAT` | AMT02 is non-negative `NNN.NN` |
| `L2-DTP-DATE8-FORMAT` | DTP with qualifier D8 has valid CCYYMMDD |
| `L2-NM1-ENTITY-TYPE-QUALIFIER` | NM102 is `1` or `2` |
| `L2-HL-LEVEL-CODE-KNOWN` | HL03 is `20` or `22` (billing / subscriber) |
| `L2-CLAIM-HAS-SERVICE-LINE` | At least one LX per claim |
| `L2-CLAIM-HAS-DIAGNOSIS` | At least one HI per claim |
| `L2-NPI-CHECK-DIGIT-VALID` | NM109 under qualifier XX passes NPI Luhn |
| `L2-DIAGNOSIS-CODE-NO-DECIMAL` | HI diagnosis codes contain no `.` |

---

## Layer 3 — DHS encounter business rules

**Module:** `validator/layer3_dhs_rules.py`  
**Authority:** `docs/reference/dhs_837_encounter_companion_guide.pdf` (each finding includes a `SOURCE:` citation in text/JSON output).

| Rule ID | What it checks |
|---------|----------------|
| `L3-BILLING-TIN-REQUIRED` | Billing provider REF*EI (TIN) in Loop 2010AA |
| `L3-BILLING-UMPI-REQUIRED` | Billing provider REF*G2 (UMPI) in Loop 2010AA |
| `L3-REFERRING-UMPI-REQUIRED` | REF*G2 when NM1*DN (referring) is present |
| `L3-RENDERING-UMPI-REQUIRED` | REF*G2 when NM1*82 (rendering) is present |
| `L3-MCO-ADJUDICATION-REQUIRED` | Loop 2320 first occurrence with MCO adjudication (AMT*D) |
| `L3-PAYER-NAME-FIXED` | Loop 2010BB payer is MN DHS (name + id) |
| `L3-RECEIVER-FIXED` | Loop 1000B receiver NM1*40 identity |
| `L3-SUBMITTER-TRADING-PARTNER-QUALIFIER` | Loop 1000A submitter NM108 = `46` |
| `L3-SENDER-ID-MATCHES-SUBMITTER` | ISA06 = GS02 = submitter NM109 |
| `L3-ISA-RECEIVER-FIXED` | ISA07=`30`, ISA08/GS03 = DHS receiver FEIN |
| `L3-MEMBER-ID-EIGHT-DIGITS` | Subscriber NM109 is 8-digit member id |
| `L3-EPSDT-NU-WHEN-NO-REFERRAL` | CRC03 = `NU` when CRC02 = `N` |
| `L3-VOID-REF-F8-ONLY` | REF*F8 only on void claims (CLM05-3=`8`) |
| `L3-DIAGNOSIS-PRINCIPAL-QUALIFIER` | First HI uses ABK |
| `L3-DIAGNOSIS-SUBSEQUENT-QUALIFIER` | Subsequent HI uses ABF |
| `L3-LINE-PAID-AMOUNT-REQUIRED-837P` | At least one line-level REF*9D (837P) |
| `L3-LINE-PAID-AMOUNT-REQUIRED-837I` | At least one line-level REF*9C (837I) |
| `L3-LINE-PAID-AMOUNT-NOT-NEGATIVE` | Line paid/allowed amounts not negative |
| `L3-CLM05-3-FREQUENCY-CODE-DOCUMENTED` | **Warning** when CLM05-3=`7` (replacement) — guide tables vs spec |
| `L3-UMPI-FORMAT-STUB` | **Stub** — produces no findings (see `KNOWN_LIMITATIONS.md`) |

---

## Layer 4 — Cross-field consistency

**Module:** `validator/layer4_consistency.py`  
**Note:** Relates multiple segments/fields on the same claim; not cited to an external PDF.

| Rule ID | What it checks |
|---------|----------------|
| `L4-CHARGE-BALANCE` | CLM02 = sum of service line charges |
| `L4-DX-POINTER-RANGE` | SV1/SV2 diagnosis pointers reference existing HI positions |
| `L4-MCO-PAID-NOT-EXCEED-CHARGE` | First 2320 AMT*D ≤ CLM02 |
| `L4-VOID-REPLACEMENT-HAS-ICN` | CLM05-3 `7`/`8` has original ICN (REF*F8 or NTE) |
| `L4-TPL-AMOUNTS-BALANCE` | TPL 2320 amounts ≤ CLM02 when TPL present |
| `L4-INSTITUTIONAL-DATE-ORDER` | 837I admission date ≤ discharge date |

---

## Severity and exit codes

| Severity | Meaning | Affects CLI/UI exit code? |
|----------|---------|---------------------------|
| `error` | Must be fixed for a clean submission | Yes — exit code `1` |
| `warning` | Documented ambiguity or advisory | No — exit code stays `0` |
| `info` | Informational (rare) | No |

Parse failures and crashes return exit code `2`.
