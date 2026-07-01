# Document Index

Audit trail for every source document this project's rules are derived from. Update
this file whenever a document is (re-)fetched or a rule module is added that cites
one of these documents.

**How to refresh "Used by" entries:** search the codebase for each PDF filename
(e.g. `rg dhs_837_encounter_companion_guide` under `src/`) and for rule IDs in
`validator/layer*_*.py`. Cross-check against [`docs/PEER_REVIEW_ACTION_PLAN.md`](../PEER_REVIEW_ACTION_PLAN.md).

All retrievals below were performed **2026-06-30**. "Used by" last verified **2026-07-01**.

---

## DHS 837 Encounter Companion Guide (primary authority)
- File: `docs/reference/dhs_837_encounter_companion_guide.pdf`
- Source URL: https://mn.gov/dhs/assets/837-encounter-companion-guide-to-the-hipaa-implementation-guide_tcm1053-629992.pdf
- Retrieved: 2026-06-30 (direct download, HTTP 200, 1,539,035 bytes)
- Version/date noted in document: Cover page states **"October 2024"**. Internal
  change-control log's most recent entry is dated **06/26/2024** ("Adding Paid
  Units" — 837P `L2400/AMT*T` and 837I `L2400/AMT*GT`). A search-engine index of
  this same URL separately reported a metadata date of **December 23, 2024**.
  **Discrepancy logged**: cover page (Oct 2024) vs. search-index metadata date
  (Dec 23 2024) vs. latest visible changelog entry (Jun 26 2024) do not all agree.
  Proceeding with the retrieved file as-is (it is the live document at the
  canonical URL today); treat "October 2024" as the document's own self-reported
  version marker for citation purposes. No newer version was found at this URL or
  via search as of the retrieval date.
- Used by:
  - **Validator Layer 3 (DHS encounter business rules)** — `src/mn_encounter_toolkit/validator/layer3_dhs_rules.py`:
    `L3-BILLING-TIN-REQUIRED`, `L3-BILLING-UMPI-REQUIRED`, `L3-REFERRING-UMPI-REQUIRED`,
    `L3-RENDERING-UMPI-REQUIRED`, `L3-MCO-ADJUDICATION-REQUIRED`,
    `L3-PAYER-NAME-FIXED`, `L3-RECEIVER-FIXED`, `L3-SUBMITTER-TRADING-PARTNER-QUALIFIER`,
    `L3-SENDER-ID-MATCHES-SUBMITTER`, `L3-MEMBER-ID-EIGHT-DIGITS`, `L3-EPSDT-NU-WHEN-NO-REFERRAL`,
    `L3-VOID-REF-F8-ONLY`, `L3-DIAGNOSIS-PRINCIPAL-QUALIFIER`, `L3-DIAGNOSIS-SUBSEQUENT-QUALIFIER`,
    `L3-LINE-PAID-AMOUNT-REQUIRED-837P`, `L3-LINE-PAID-AMOUNT-REQUIRED-837I`,
    `L3-LINE-PAID-AMOUNT-NOT-NEGATIVE`, `L3-CLM05-3-FREQUENCY-CODE-DOCUMENTED`,
    `L3-UMPI-FORMAT-STUB` (stub — zero findings by design; see `KNOWN_LIMITATIONS.md`).
  - **Validator Layer 1 (envelope, DHS-specific elements)** — `validator/layer1_envelope.py`:
    `L1-ONE-ISA-PER-FILE`, `L1-SEPARATORS-DISTINCT` (ISA11 repetition separator `]`).
  - **837 writer field mappings** — `edi/writer.py` (per-segment `SOURCE:` comments for
    loops 1000A/B, 2010AA/BB, 2320, 2400, envelope).
  - **X12 separator defaults** — `edi/x12_core.py` (`Separators`, `detect_separators`).
  - **Data models** — `models/core.py`, `models/encounter.py` (`FrequencyCode`, service
    line paid-amount semantics, DHS payer constants).
  - **Synthetic scenario builders** — `generator/scenarios/atypical.py`, `tpl.py`,
    `void_replacement.py`, `errors.py`, `misc.py`, `common.py`; `generator/entities.py`.
  - **Identifier generation** — `identifiers/tin.py`; `identifiers/umpi.py` (format
    assumed — see `KNOWN_LIMITATIONS.md`).
  - **Tests** — `tests/unit/test_layer3_dhs_rules.py` and integration scenarios that
    assert DHS rule IDs (see `tests/integration/test_pipeline.py`).
- Notes: This is the **sole authority** for MN encounter-specific business rules
  (Layer 3). It covers Professional, Institutional, and Dental claims in one
  document. It takes precedence over all AUC MUCGs below wherever they differ for
  encounter submissions. Contains a DHS Requirements Value Column and a Req'd
  column (Y / N / C1 / C2) per element — this is the structure Layer 3 rules should
  walk.

## AUC MUCG for 999 / TA1
- File: `docs/reference/mucg_999_ta1.pdf`
- Source URL: https://www.health.state.mn.us/facilities/ehealth/auc/guides/docs/cgta1.pdf
- Retrieved: 2026-06-30 (direct download, HTTP 200, 80,942 bytes)
- Version/date noted in document: **Version 4.0, adopted into rule May 23, 2016**
  (revision history table in-document: v1.0 9/27/2010 → v2.0 12/27/2010 → v3.0
  12/14/2015 → v4.0 5/23/2016). Matches the version found via search-cache of the
  AUC index page — no discrepancy.
- Used by:
  - **999 generator** — `src/mn_encounter_toolkit/response/gen_999.py` (module docstring:
    MN guide adopts base X12 005010X231 by reference; generator implements AK1/AK2/AK3/AK5/AK9
    per base IG). Deterministic mode also runs `validator/layer1_envelope.py` and
    `validator/layer2_syntax.py` against the input 837 (envelope/syntax scope of a 999).
  - **Tests** — `tests/unit/test_gen_999.py`, `tests/integration/test_pipeline.py`.
  - **Note:** This PDF covers **TA1** specifically; full 999 structure comes from the
    incorporated base X12 005010X231 TR3, not restated in the MN one-pager.
- Notes: Covers the **TA1** Interchange Acknowledgment segment specifically (not
  the full 999 transaction structure). Use base X12 005010X231 TR3 for general 999
  AK1/AK2/AK9 structure; this guide governs MN-specific TA1 usage. Secondary
  reference only — DHS encounter 999s are governed primarily by DHS's own encounter
  acknowledgment process (see `dhs_encounter_data_landing_rendered.md`), with this
  guide as a fallback for base TA1/999 syntax not addressed there.

## AUC MUCG for 835
- File: `docs/reference/mucg_835.pdf`
- Source URL: https://www.health.state.mn.us/facilities/ehealth/auc/guides/docs/cg835.pdf
- Retrieved: 2026-06-30 (direct download, HTTP 200, 640,624 bytes)
- Version/date noted in document: **Version 14.0, adopted as a rule August 12,
  2019**, "supersedes all previous versions ... remains in force until superseded."
  The AUC index page cache did not clearly surface a version/date for this specific
  row (table truncated in the search synthesis) — **not treated as a conflict**,
  just unconfirmed against the live index table; the in-document statement is
  authoritative and unambiguous.
- Used by:
  - **835E generator** — `src/mn_encounter_toolkit/response/gen_835e.py` (BPR/TRN/N1/CLP/SVC/CAS
    structure; Sec 2.4 transaction table, Sec 2.1.2.3 payee = 837 billing provider, Appendix C
    worked examples). Module docstring cites `dhs_encounter_data_landing_rendered.md` for the
    encounter-vs-FFS authority distinction.
  - **CARC/RARC pool** — `src/mn_encounter_toolkit/response/carc_rarc.py` (Appendix A delegates
    to national code lists; toolkit uses a curated subset — see `KNOWN_LIMITATIONS.md`).
  - **Tests** — `tests/unit/test_gen_835e.py`, `tests/integration/test_pipeline.py`.
- Notes: This is a **standard 835 MUCG**, not encounter-specific. Per the DHS
  landing page, DHS's own 835 (called 835E in this project's spec) for encounters
  is a distinct variant with encounter-specific remark codes. This MUCG is the
  fallback for base 835 syntax/CARC-RARC usage (Appendix A) not addressed by
  DHS-specific encounter material; it is NOT the authority for encounter-specific
  remark codes or adjudication indicators. DHS-specific 835E behavior must come
  from the DHS 837 Encounter Companion Guide and/or DHS encounter landing-page
  linked resources (see Known Limitations — those linked PDFs were not directly
  extractable due to the page being JS-rendered).

## AUC MUCG for 837P
- File: `docs/reference/mucg_837p.pdf`
- Source URL: https://www.health.state.mn.us/facilities/ehealth/auc/guides/docs/cg837p.pdf
- Retrieved: 2026-06-30 (direct download, HTTP 200, 346,063 bytes)
- Version/date noted in document: **Version 18.0** ("MUCG v18.0 for the
  Implementation of the X12/005010X222A1 Health Care Claim: Professional (837)").
  Internal file path breadcrumb on page 2 references "2023" drafting; AUC index
  page cache confirms **adopted 1/10/24**. Consistent — no discrepancy.
- Used by:
  - **Validator Layer 2 (base X12/TR3 syntax)** — `src/mn_encounter_toolkit/validator/layer2_syntax.py`
    (rules implement X12 005010X222A1 / 005010X223A2 encounter-claim syntax; **no per-rule
    `source_citation` in code** — Layer 2 is intentionally distinguished from Layer 3 DHS rules):
    `L2-ST01-VALUE`, `L2-BHT-PRESENT`, `L2-CLM-EXACTLY-ONE-PER-CLAIM`, `L2-CLM02-MONEY-FORMAT`,
    `L2-AMT02-MONEY-FORMAT`, `L2-DTP-DATE8-FORMAT`, `L2-NM1-ENTITY-TYPE-QUALIFIER`,
    `L2-HL-LEVEL-CODE-KNOWN`, `L2-CLAIM-HAS-SERVICE-LINE`, `L2-CLAIM-HAS-DIAGNOSIS`,
    `L2-NPI-CHECK-DIGIT-VALID`, `L2-DIAGNOSIS-CODE-NO-DECIMAL`.
  - **Tests** — `tests/unit/test_layer2_syntax.py`.
  - **Note:** This MUCG documents **FFS** professional claims; per DHS encounter landing page
    text it is **not** authoritative for MCO encounter submissions. It informs Layer 2 only where
    rules match base TR3 structure not contradicted by the DHS Encounter Companion Guide.
- Notes: This is the **general FFS provider-claim** companion guide, explicitly
  **not** the authority for encounter-specific rules (DHS's own landing page states
  AUC/MN-ITS companion guides "should not be referenced for submitting your
  encounter claims"). Used only as a secondary reference for base X12 TR3
  syntax/structure that is common to both FFS and encounter 837P and not
  contradicted by the DHS Encounter Companion Guide. Any rule sourced from this
  document must be flagged as "base TR3 syntax" (Layer 2), never cited as a DHS
  encounter business rule (Layer 3).

## AUC index page (version-check reference)
- File: `docs/reference/mucg_index_cached_snapshot.md` (reconstructed content) and
  `docs/reference/mucg_index_403_antibot_challenge_page.html` (the literal HTTP 403
  response body captured during retrieval — confirms an anti-bot challenge page
  rather than real content; contains an `antibot` CSS class reference and a Google
  Tag Manager snippet, not the guide index)
- Source URL: https://www.health.state.mn.us/facilities/ehealth/auc/guides/index.html
- Retrieved: **FAILED — direct retrieval blocked, 2026-06-30**
  - Error: HTTP 403 Forbidden on every direct attempt:
    - Plain `Invoke-WebRequest` / `curl.exe` GET → 403
    - With `Referer` header set to the parent AUC page → 403
    - Via alternate CDN subdomains (`www2cdn.web.health.state.mn.us`,
      `www.web.health.state.mn.us`) → 403
    - Via the agent's rendering-fetch tool → request timeout (2 attempts)
  - All other paths on the same domain (site root, the four guide PDFs themselves,
    a sibling `/auc/index.html` page) returned HTTP 200 in the same session, so this
    is a path-specific block (response carries `Vary: Cookie`, suggesting a
    cookie/JS challenge gates this one path), not a domain-wide outage.
  - **Alternate retrieval attempted per the fallback procedure**: searched
    `site:health.state.mn.us AUC companion guides index` and a follow-up version
    query; a search-engine cache of the live page content was returned and used to
    reconstruct version/date data (see `mucg_index_cached_snapshot.md`). This is a
    partial reconstruction, not the literal page bytes.
- Version/date noted in document: Cached snapshot shows **"Last Updated:
  03/01/2024"** on the index page itself.
- Used by: version cross-check only; not a rule source.
- Notes: **Action item for a future session**: if exact byte-for-byte confirmation
  of this page is ever required, retrieve it with a real browser (the project's
  browser-automation tooling, not a plain HTTP client) since the block appears to
  be a cookie/JS bot-challenge. Logged in `KNOWN_LIMITATIONS.md`.

## DHS MCO Encounter Data landing page
- File: `docs/reference/dhs_encounter_data_landing.html` (raw, JS-shell only) and
  `docs/reference/dhs_encounter_data_landing_rendered.md` (rendered text capture)
- Source URL: https://mn.gov/dhs/partners-and-providers/policies-procedures/minnesota-health-care-programs/provider/mcos/encounter-data/
- Retrieved: 2026-06-30 (raw HTML: direct download, HTTP 200, 21,621 bytes; content
  capture: rendering fetch, succeeded)
- Version/date noted in document: not stated (no revision date on page itself)
- Used by: context/orientation and authority-boundary notes in:
  `response/gen_835e.py`, `response/carc_rarc.py`, `KNOWN_LIMITATIONS.md`, `docs/ARCHITECTURE.md`.
  Confirms MCO-vs-FFS distinction, 999/835 biweekly cycle, and that AUC MUCGs are **not**
  authoritative for encounter submissions.
- Notes: **Partial retrieval** — the page is a JavaScript single-page-app shell.
  The raw HTML download contains only 2 `<a>` tags and no real content (all
  sections render client-side). A rendering-capable fetch captured the visible text
  (saved as the `_rendered.md` file), but the **actual linked PDF URLs behind each
  accordion section** ("Encounter submission guides", "File submission
  acknowledgement guides", "Remittance Advice and Capitation Payment Guides", etc.)
  could not be extracted without full browser automation (JS click-to-expand
  accordions). This is the one required document where "additional linked
  resources" could not be fully enumerated. Logged in `KNOWN_LIMITATIONS.md` as a
  follow-up item — likely worth a browser-automation pass before Layer 3 is
  finalized, since these accordion links may contain encounter-specific 999/835E
  detail not in the DHS 837 Encounter Companion Guide.
  - Confirmed directly from this page's text: AUC/MN-ITS companion guides are
    explicitly NOT authoritative for encounter submissions (supports this
    project's core premise).
  - A sibling page discovered via search (not fetched, not required):
    `.../mcos/encounter-data/biweekly-processing-cycle/` — confirms encounter
    acknowledgment is 999 (X12 837 family) / N11R (NCPDP pharmacy), and remittance
    is X12 835, delivered biweekly to the MCO's MN-ITS mailbox.
