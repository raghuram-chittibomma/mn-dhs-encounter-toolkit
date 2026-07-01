# AUC Minnesota Uniform Companion Guides — index page (cached snapshot)

> **Retrieval note**: Direct HTTP retrieval of
> `https://www.health.state.mn.us/facilities/ehealth/auc/guides/index.html` was
> blocked by the site's CloudFront/WAF layer (HTTP 403 on every attempt — direct
> download, `curl`, alternate CDN subdomains `www2cdn.web.health.state.mn.us` and
> `www.web.health.state.mn.us`, and a JS-rendering fetch all returned 403; the
> response header `Vary: Cookie` suggests a cookie/JS challenge gates this specific
> path). All *other* probed paths on the same domain — including the actual guide
> PDFs in this index — returned HTTP 200 without issue, so the block is specific to
> this index path, not the whole domain.
>
> The content below was reconstructed from a search-engine cache/synthesis of the
> live page (retrieved via web search, not a direct page fetch) on 2026-06-30. It is
> a **partial reconstruction**, not a byte-for-byte copy of the page. Treat the
> version/date values below as good-faith but unverified-against-source-HTML; the
> companion PDFs themselves (fetched directly, HTTP 200) are the authoritative
> source for version numbers and are what `DOCUMENT_INDEX.md` keys off of.

## Page metadata observed in cache
- Page title: "AUC Minnesota Uniform Companion Guides"
- **Last Updated: 03/01/2024** (as shown in cached snapshot)
- Section heading observed: "v5010/D.0"

## Relevant table rows reconstructed from cache

| Guide | PDF | Version | Date |
|---|---|---|---|
| Health Care Claim: Professional (837) | `cg837p.pdf` | V18.0 | 1/10/24 |
| Health Care Claim: Institutional (837) | `cg837i.pdf` | V18.0 | 1/10/24 |
| Health Care Claim: Dental (837) | `cg837d.pdf` | V12.0 | 8/14/17 |
| Eligibility Benefit Inquiry (270/271) | `cg2700271.pdf` | V14.0 | 4/4/24 |

The cache did not surface the 835 and 999/TA1 rows' version text directly (table
truncated in the search synthesis), but those values were independently confirmed
from the **first page of the downloaded PDFs themselves**:
- `mucg_835.pdf` → "Minnesota Uniform Companion Guide (MUCG) Version 14.0 ... Adopted as a rule on August 12, 2019"
- `mucg_999_ta1.pdf` → "Minnesota Uniform Companion Guide version 4.0 ... adopted into rule on May 23, 2016"

## Note on cg837i.pdf
An AUC MUCG for 837 Institutional (`cg837i.pdf`, V18.0, 1/10/24) exists at the same
path pattern as `cg837p.pdf` but was **not** in this project's required document
list and was not fetched. Per the DHS landing page content (see
`dhs_encounter_data_landing_rendered.md`), DHS explicitly states the AUC/MN-ITS
companion guides "should not be referenced for submitting your encounter claims" —
institutional encounter rules should come from the DHS 837 Encounter Companion
Guide (which covers Professional, Institutional, and Dental together), not from the
AUC 837I MUCG. Flagged here for awareness only; not treated as a gap.
