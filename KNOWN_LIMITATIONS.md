# Known Limitations

Tracks implemented vs. stubbed vs. deferred work, and any source-document gaps.
Update at the end of each working session. See [`docs/SPEC.md`](docs/SPEC.md)
for the original project requirements this is tracked against.

## Document acquisition (2026-06-30)

- **AUC index page unreachable directly.**
  `https://www.health.state.mn.us/facilities/ehealth/auc/guides/index.html` returns
  HTTP 403 on every direct-HTTP retrieval attempt (plain request, with referer,
  via two alternate CDN subdomains), while every other probed path on the same
  domain — including the four target PDFs — returned 200. The response carries
  `Vary: Cookie`, consistent with a cookie/JS bot-challenge scoped to this one
  path. Worked around via a search-engine cache reconstruction (see
  `docs/reference/mucg_index_cached_snapshot.md`), which is sufficient to confirm
  version numbers for the 837P guide but is a partial reconstruction, not the full
  page. **Follow-up**: if full content of this page is needed later, fetch it with
  real browser automation rather than a plain HTTP client.

- **DHS encounter landing page is JS-rendered; accordion links not extracted.**
  `https://mn.gov/dhs/.../encounter-data/` is a single-page-app shell — the raw
  HTML has no real body content. A rendering-capable fetch captured the visible
  text (`docs/reference/dhs_encounter_data_landing_rendered.md`), confirming the
  MCO-vs-FFS distinction and section headers, but the **PDF URLs behind each
  accordion section** (e.g. "Remittance Advice and Capitation Payment Guides",
  "File submission acknowledgement guides") could not be enumerated without
  clicking through JS accordions. These sections may contain DHS-specific 999/835E
  detail (e.g. encounter remark codes, MN-ITS file naming convention for 999) that
  isn't in the DHS 837 Encounter Companion Guide. **Follow-up**: a browser-
  automation pass over this page is recommended before Layer 3 / 999 / 835E
  generator work is finalized, specifically to check for a dedicated encounter 999
  naming-convention document and any encounter-specific 835E remark-code list.

- **Document date discrepancy on the DHS 837 Encounter Companion Guide.** The
  document's own cover page says "October 2024"; its internal change-control log's
  newest visible entry is dated 06/26/2024; a search-engine's indexed metadata for
  the same URL reported December 23, 2024. All three are plausibly consistent with
  normal publish/revise/re-index lag, but they don't literally agree. Logged in
  `docs/reference/DOCUMENT_INDEX.md`; proceeding with the document as currently
  published at the canonical URL (no newer version found at that URL or via
  search). Not currently blocking — no rule logic has been written yet.

## Rules / code

Per the working process, every `# TODO: VERIFY AGAINST [doc]` / `# TODO: AMBIGUOUS
IN SOURCE` stub added to the codebase is listed here with its file location.

- **837I paid/allowed REF qualifier placement (fixed 2026-07).** Prior versions
  wrote and validated `REF*9A`/`REF*9C` at the 2400 line level; the companion
  guide assigns those qualifiers to loop 2300 (claim total) and `REF*9B`/`REF*9D`
  to loop 2400. See `docs/LAYER3_GAP_RESOLUTION.md`.

- **UMPI format/length unconfirmed.** `identifiers/umpi.py` and
  `validator/layer3_dhs_rules.py` (`rule_umpi_format_documented` stub area, ~line
  421) — the companion guide references REF*G2 as "the DHS UMPI number" wherever
  it appears (Loop 2010AA/2310A/2310B/2310C/2310D, p.13-22 / p.37-44) but never
  states a character length or format. `identifiers/umpi.py` assumes an 8-digit
  numeric string as a reasonable synthetic default; this is *not* confirmed
  against any retrieved source.

- **CLM05-3 = "7" (replacement) not in the guide's own value table.** The DHS
  837 Encounter Companion Guide's CLM05-3 value table only enumerates "1"
  (original) and "8" (void); the task spec mandates "7" for replacements
  (the base 837 TR3's standard value). `models/encounter.py` /
  `generator/scenarios/void_replacement.py` follow the spec's explicit
  instruction; `validator/layer3_dhs_rules.py`
  `rule_clm05_3_frequency_code_documented` (~line 394) flags code "7" usage as
  a **warning** (not an error) precisely because of this guide/spec conflict,
  pending DHS clarification.

- **Institutional DRG reporting on the *encounter* (837I) is unconfirmed.**
  `models/encounter.py` (~line 135) — DRG/APR-DRG reporting is documented for
  the *835* response (`mucg_835.pdf` Appendix E, REF*CE "APRDRG=" format) but
  no equivalent 837I *encounter* segment/element was found in
  `dhs_837_encounter_companion_guide.pdf`. `InstitutionalDetail.drg_code` is
  carried as generator/test metadata only and is **not** written to the 837I
  output by `edi/writer.py`.

- **CARC/RARC code values are not enumerated by mucg_835.pdf itself.**
  `response/carc_rarc.py` — Appendix A ("Requirements and instructions for
  CARC, RARC, and CAGC use", p.15-16) explicitly delegates the actual code
  *values* to external national maintainers (Washington Publishing Company for
  CARC/RARC, CMS for RARC content, CAQH-CORE for required combinations); none
  of those external code-list documents were retrieved. The pool used by the
  835E generator is a small set of long-stable, widely-known public CARC/RARC
  codes selected for plausibility, not sourced from a DHS/MN-specific list.

- **835E has no confirmed DHS-specific structural specification.**
  `response/gen_835e.py` (module docstring) — `mucg_835.pdf` is the *base*
  AUC 835 companion guide, and the DHS encounter-data landing page
  (`docs/reference/dhs_encounter_data_landing_rendered.md`) explicitly states
  AUC MUCGs do not apply to MCO encounter submissions/responses. The generator
  adapts the base 835's CLP/SVC/CAS/AMT mechanics (mucg_835.pdf Appendix C
  worked examples, p.19-25) to an "DHS acknowledges the MCO-reported
  adjudication" interpretation (sender=DHS, payee=837 billing provider per
  Sec 2.1.2.3) — this is this project's own reasonable construction, not a
  confirmed DHS encounter-835E format.

- **DHS encounter landing page accordion links never resolved (carried
  forward from document acquisition).** No browser-automation follow-up was
  performed before Layer 3 / 999 / 835E were finalized (see entry above from
  2026-06-30); the two limitations directly attributable to this gap are the
  UMPI format and the 835E structure items above. If a future pass retrieves
  the linked "Remittance Advice and Capitation Payment Guides" / "File
  submission acknowledgement guides" documents, revisit both.
