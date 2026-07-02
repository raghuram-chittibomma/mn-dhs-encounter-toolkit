# TC-QA-023 — Guide-derived 837I checklist

**Source:** `docs/reference/dhs_837_encounter_companion_guide.pdf` (October 2024)  
**Fixture:** `qa-uat/test-data/inputs/qa_clean_837i_seed42.x12`  
**Review date:** 2026-07-02

| Loop / Segment | Element / qualifier | Req (guide) | Guide page | Present in fixture | Notes |
|----------------|---------------------|-------------|------------|-------------------|-------|
| L2010AA | NM1 billing provider | Y | 38 | Yes (NM1*85) | Org name, NPI C1 |
| L2010AA | REF*EI tax ID | Y | 39 | Yes | |
| L2010AA | REF*G2 UMPI | C1 | 41 | Yes (REF*G2*61559407) | Billing provider secondary ID |
| L2010BA | DMG subscriber demographics | Y | 40 | Yes (DMG*D8) | Birth date + gender |
| L2010BA | NM1*IL member ID (8-digit) | Y | 39–40 | Yes (MI*16475255) | |
| L2300 | DTP*434 statement dates | Y | 42 | Yes | RD8 from–through |
| L2300 | DTP*435 admission date/hour | C1 | 43 | Yes | DT format |
| L2300 | DTP*096 discharge hour | C1 | 42 | Yes | TM 1400 |
| L2300 | CL1 institutional claim code | Y | 43 | Yes (CL1*3*2*01) | Admission type + source + status |
| L2300 | NTE*UPI patient account | Y (effective 2/1/17) | 8, 44 | Yes (PAC=…) | Required on all 837I |
| L2310A | NM1*71 attending physician | C1 | 50–51 | Yes | NPI XX qualifier |
| L2310A | REF*G2 attending UMPI | C2 | 51 | Yes | Secondary identifier |
| L2310E | NM1*77 service facility | C1 | 51–52 | Yes | |
| L2310E | REF*G2 facility UMPI | C1 | 51–52 | Yes | |
| L2400 | REF*9B allowed (line) | C2 | 43–44 | Yes | Per appendix paid/allowed placement |
| L2400 | REF*9D paid (line) | C2 | 43–44 | Yes | MCO-paid at line level |
| L2400 | AMT*GT paid units | Y (06/26/2024 addendum) | 10 | Yes | Format XXX.00 |

**Validation:** full L1–4 exit 0, zero error-level findings (see `TC-QA-023_validate.json`).

**Gaps noted (informational, not failures):** Claim-level REF*9A/9C (allowed/paid at header) are C2 per guide appendix; fixture uses line-level 9B/9D which validated clean.
