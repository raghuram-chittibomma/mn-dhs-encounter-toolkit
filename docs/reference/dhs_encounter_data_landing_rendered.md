# DHS MCO Encounter Data landing page — rendered text capture

> **Retrieval note**: The page at
> `https://mn.gov/dhs/partners-and-providers/policies-procedures/minnesota-health-care-programs/provider/mcos/encounter-data/`
> is a JavaScript-rendered single-page-app shell. The raw HTML saved as
> `dhs_encounter_data_landing.html` (HTTP 200, downloaded directly) contains only 2
> `<a>` tags and no real body content — the accordion sections below are populated
> client-side and are not present in the static HTML. The text below was captured
> via a rendering fetch on 2026-06-30 and is the best available text snapshot of
> the page's content without browser automation.

# Managed care organizations - Encounter submissions

The Department of Human Services (DHS) requires that HIPAA transaction formats be
applied to encounter submissions. This page includes Minnesota Health Care Programs
(MHCP) guides and other documents that will assist you in understanding:

- Encounter file submission requirements
- Other encounter transactions
- MHCP encounter claim processing cycles

Any questions on the content of this page should be directed to:
DHS.edqunit@state.mn.us

## Encounter data submissions instructions and references

### MHCP Companion Guides

DHS requires MCOs to submit encounter professional/institutional/dental claims in
the X12 format. Encounter pharmacy claims must be submitted in the NCPDP Batch
format.

> **"Please note that the companion guides referenced on the MN–ITS website are not
> encounter claim guides and should not be referenced for submitting your encounter
> claims."**

This is DHS's own explicit confirmation of the distinction this project's spec is
built around: the AUC MUCGs (MN-ITS / fee-for-service) are NOT authoritative for
encounter submissions; the DHS 837 Encounter Companion Guide is.

Accordion section headers observed (link targets not extractable without browser
rendering — see `KNOWN_LIMITATIONS.md`):
- Encounter submission guides
- File submission acknowledgement guides
- Remittance Advice and Capitation Payment Guides
- Testing X12 837 and NCPDP Batch File Submissions
- Testing syntax for TPL data elements and MCO Paid Dates on 837 claim types
- File Submission/Processing Schedule
- Supplemental Information for Encounter Claim Submission and Processing
- Quality Assurance Protocols (QAPs)
- MCO Denied Claims and Claim Penalties

A related sibling page found via search and worth noting for future reference:
`.../mcos/encounter-data/biweekly-processing-cycle/` — describes the biweekly
submission/processing/remittance cycle (Wednesday 11:59pm cutoff, Saturday
processing, Friday-following-week 835 remittance delivery) and confirms encounter
acknowledgments are **999** (Professional/Institutional/Dental) and **N11R**
(Pharmacy), and that the remittance advice is **X12 835** delivered to the MCO's
MN-ITS mailbox. Not fetched/saved as it was not in the required document list, but
relevant for understanding the submission cycle.
