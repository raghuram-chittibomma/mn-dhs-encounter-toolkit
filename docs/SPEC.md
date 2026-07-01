# MN DHS Encounter EDI Toolkit -- Project Specification

> **Provenance**: this is the original requirements document that guided this
> project's design and implementation, given on 2026-06-30. It defines *what*
> the toolkit must do; the *how* (data models, libraries, project structure,
> language features) was worked out separately -- see the architecture
> proposal that was reviewed and approved before implementation began, and
> [`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md) for where the
> implementation had to resolve ambiguity or document gaps against this spec.
> Stored here verbatim so it remains the canonical reference for "is the
> toolkit doing what was asked" without depending on chat history.

This document defines **what** the toolkit must do. Technical decisions —
data models, libraries, project structure, language features — are yours to
make. Propose your approach before generating significant code, and flag any
requirement that is ambiguous or conflicts with your chosen approach.

---

## Context and submission model

This toolkit is specifically for **MCO encounter data submissions** to
Minnesota DHS — not fee-for-service provider billing. Understanding this
distinction is essential before writing any rule logic.

### Who submits what to whom

- **Submitter**: a Managed Care Organization (MCO) contracted with Minnesota
  DHS to provide prepaid health care services under PMAP, MinnesotaCare,
  MSHO, MSC+, or Special Needs BasicCare (SNBC).
- **Transaction**: the MCO submits **837 encounter files** to DHS reporting
  services that network providers delivered to MCO-enrolled members. These
  are not provider billing claims — they are encounter records the MCO is
  required to report.
- **Receiver / payer**: Minnesota DHS, operating through the **MN–ITS**
  system.
- **DHS responses**: DHS returns a **999** (Implementation Acknowledgment)
  for every submitted batch and an **835E** (encounter remittance) reporting
  adjudication results.

### Primary authority document

The governing rule document for this toolkit is the **DHS 837 Encounter
Companion Guide**, published by Minnesota DHS for MCO encounter submissions.
This document is distinct from the general AUC Minnesota Uniform Companion
Guides (MUCGs) used for fee-for-service provider claims. The DHS Encounter
Companion Guide takes precedence over the AUC MUCGs wherever the two differ
for encounter submissions.

---

## Document acquisition — first task before any rule logic

**Before writing any Minnesota-specific validation rules or response
generation logic, Cursor must fetch, save, and index the authoritative
source documents.** This is the first task in the project, not a background
step.

### Required documents and their known URLs

Fetch each document, save it to `docs/reference/` in the project, and log
the retrieval in `docs/reference/DOCUMENT_INDEX.md`. Cursor owns this
retrieval — do not ask me for these files.

| Document | Known URL | Save as |
|---|---|---|
| DHS 837 Encounter Companion Guide (primary authority) | `https://mn.gov/dhs/assets/837-encounter-companion-guide-to-the-hipaa-implementation-guide_tcm1053-629992.pdf` | `dhs_837_encounter_companion_guide.pdf` |
| AUC MUCG for 999 / TA1 | `https://www.health.state.mn.us/facilities/ehealth/auc/guides/docs/cgta1.pdf` | `mucg_999_ta1.pdf` |
| AUC MUCG for 835 | `https://www.health.state.mn.us/facilities/ehealth/auc/guides/docs/cg835.pdf` | `mucg_835.pdf` |
| AUC MUCG for 837P | `https://www.health.state.mn.us/facilities/ehealth/auc/guides/docs/cg837p.pdf` | `mucg_837p.pdf` |
| AUC index page (to check for updated versions of any of the above) | `https://www.health.state.mn.us/facilities/ehealth/auc/guides/index.html` | `mucg_index.html` |
| DHS MCO Encounter Data landing page (for any additional linked resources) | `https://mn.gov/dhs/partners-and-providers/policies-procedures/minnesota-health-care-programs/provider/mcos/encounter-data/` | `dhs_encounter_data_landing.html` |

### If a URL is unreachable

If any URL returns an error or the file cannot be retrieved:
1. Log the failure in `DOCUMENT_INDEX.md` with the URL, date attempted, and
   HTTP status or error received.
2. Search for an alternate URL for the same document using the document
   title and `site:mn.gov` or `site:health.state.mn.us` before giving up.
3. If the document genuinely cannot be retrieved, write a stub rule file
   with a `# BLOCKED: source document unavailable — rules here are
   placeholders only` header, and flag it clearly in `KNOWN_LIMITATIONS.md`.

### Document index format

`docs/reference/DOCUMENT_INDEX.md` must be maintained throughout the project
with this structure for each document:

```
## [Document name]
- File: docs/reference/[filename]
- Source URL: [url]
- Retrieved: [date]
- Version/date noted in document: [version string found in the PDF, or "not stated"]
- Used by: [list of source modules that derive rules from this document]
- Notes: [any version warnings, retrieval issues, or caveats]
```

This file is the audit trail — anyone reading the project should be able to
see exactly which document version drove which rules.

### Version checking

When fetching documents, check the AUC index page and the DHS encounter data
landing page for any notices of document updates. If a retrieved document's
internal version number or date differs from what this prompt references,
log the discrepancy in `DOCUMENT_INDEX.md` and proceed with the retrieved
version. Do not silently assume the version is current.

### Rule derivation traceability

Every validation rule in Layer 3 (MN business rules) and every
response-generation behavior that derives from a companion guide must
include a code comment citing the source document and, where possible, the
section or segment table row it came from. Example:

```python
# SOURCE: dhs_837_encounter_companion_guide.pdf — Loop 2010AA, NM109 element
# DHS requires UMPI as secondary identifier for providers enrolled in MHCP.
```

This makes it possible to audit rules against the document and to identify
which rules need review when a document is updated.

---

## Non-negotiable constraints

- **Transaction sets in scope**:
  - **837P** (X12 005010X222A1) — professional encounter submissions from
    MCOs
  - **837I** (X12 005010X223A2) — institutional encounter submissions from
    MCOs
  - **999** (Implementation Acknowledgment) — DHS response to a submitted
    batch
  - **835E** (X12 005010X221A1, encounter remittance variant) — DHS
    adjudication response to encounter submissions
- **Python 3.11+** runtime.
- **No real PII** in synthetic data — all generated entities must be
  clearly fictional.
- **Testability**: every validation rule must be individually testable in
  isolation without requiring a full EDI file as input.
- **Portability**: runs from the command line; no server or database
  required.

---

## Encounter-specific concepts that must be understood before implementation

These concepts drive encounter-specific validation rules and synthetic data
generation. Confirm your understanding of each before writing rule logic,
using the retrieved companion guide as the source.

### MCO as submitter, not provider
The ISA/GS submitter in an encounter file is the **MCO**, not the rendering
provider. The MCO's trading partner ID with DHS appears in ISA06. Provider
identity appears in inner loops. Validation must distinguish between
MCO-level and provider-level identifiers — confusing them is a common source
of incorrect rule implementation.

### UMPI (DHS provider identifier)
Minnesota DHS assigns a **UMPI** number to providers enrolled in MHCP. In
encounter submissions, the UMPI appears in provider identifier loops. For
atypical providers (those without an NPI under MN statute), TIN is the
primary identifier and UMPI is the secondary with qualifier **G2**. Exact
placement and format must come from the retrieved companion guide.

### MCO-paid amount
Encounters must include the amount the MCO actually paid to the rendering
provider (or $0 for denied/unpaid encounters). This is a DHS-specific
requirement not present in standard fee-for-service 837 submissions. The
segment and element for this must be confirmed from the companion guide.

### Third Party Liability (TPL)
When a member has other insurance, the encounter must report TPL payer
information and amounts in COB loops (up to 10 SBR loops). TPL is a
significant source of encounter errors and must be covered in synthetic
scenarios and validation rules.

### Void and replacement encounters
- **Void** (CLM05-3 = 8): reverses a previously accepted encounter; must
  carry the MCO's original claim ICN in the appropriate REF segment.
- **Replacement** (CLM05-3 = 7): corrects a previously accepted encounter;
  must carry the original ICN.

Validation must check that void/replacement encounters carry the required
ICN reference.

### EPSDT (Early and Periodic Screening, Diagnostic, and Treatment)
Teen Checkup and EPSDT encounters carry specific CRC segment values as
required by the DHS companion guide. Cover in validation rules and in at
least one synthetic scenario.

### 835E vs. standard 835
DHS returns an **835E** — an encounter-specific remittance variant — not a
standard provider remittance. It includes encounter-specific remark codes
and adjudication indicators. Confirm 835E-specific requirements from the
retrieved companion guide before implementing the response generator.

---

## Capability 1: Synthetic Encounter Data Generation

### Purpose
No real source data is available. The toolkit must generate realistic,
internally consistent synthetic data end-to-end — from MCO and provider
entities through member enrollment to complete 837P and 837I encounter files
— as the input corpus for the validator and response generators.

### What the generator must produce

**MCOs**: fictional MCO entities with a synthetic MN DHS trading partner
ID, payer ID for ISA/GS submitter fields, and program configuration (PMAP,
MinnesotaCare, MSHO, MSC+, SNBC) and county-of-operation profile.

**Providers**: individual and organizational providers who rendered
services to MCO members, carrying NPI (must pass the standard 10-digit
Luhn check — implement this correctly), UMPI, TIN, taxonomy code, and a
standard vs. atypical designation. Minnesota addresses drawn from real MN
city/ZIP combinations (Twin Cities metro, Duluth, Rochester, and outstate
MN); fictional street addresses only.

**Members**: MCO-enrolled individuals with fictional MN Medicaid IDs, MCO
member IDs, MHCP program enrollment, county of residence, demographics, and
TPL status (whether the member has other insurance that requires COB
loops).

**Encounters**: complete encounter records covering all fields required to
produce a valid 837P or 837I, including:
- Encounter type (837P or 837I) and subtype (original, replacement with
  ICN, or void with ICN)
- MCO-paid amount (may be $0)
- TPL/COB information where applicable
- Diagnoses (ICD-10-CM), procedures (CPT/HCPCS for 837P; revenue codes for
  837I), POA indicators (837I inpatient)
- EPSDT indicators where applicable
- All charge, payment, and adjustment amounts that must balance

**MN-realistic reference data**: diagnosis pools weighted toward conditions
common in MN Medicaid/MCO populations (behavioral health F-codes,
substance use, chronic conditions, maternal/child health, developmental
disabilities, injuries); procedure pools covering services common in MN
MCO networks (E&M, behavioral health H-codes, LTSS/waiver HCPCS,
preventive, lab, radiology); revenue codes and ICD-10-PCS for 837I.

### Named generation scenarios

The generator must support named, reproducible scenarios. Required at
minimum:

| Scenario | What it represents |
|---|---|
| `clean_professional_original` | Valid 837P original encounter, standard provider, MCO-paid amount present, no TPL |
| `clean_institutional_original` | Valid 837I original, inpatient, admission/discharge dates, DRG, MCO-paid amount |
| `professional_with_tpl` | 837P with TPL payer present, COB loops populated |
| `institutional_with_tpl` | 837I with TPL payer |
| `void_encounter` | Void (CLM05-3=8) with original MCO ICN reference |
| `replacement_encounter` | Replacement (CLM05-3=7) with original ICN |
| `epsdt_teen_checkup` | 837P with EPSDT/Teen Checkup CRC codes |
| `atypical_provider` | No NPI: TIN as primary, G2 qualifier, UMPI as secondary |
| `pmap_professional` | PMAP-enrolled member, professional encounter |
| `minnesotacare_professional` | MinnesotaCare-enrolled member |
| `msho_institutional` | MSHO-enrolled member, inpatient |
| `zero_paid_encounter` | MCO paid $0 to provider |
| `multi_provider` | Billing provider differs from rendering provider |
| `err_missing_umpi` | UMPI required but absent — MN rule violation |
| `err_missing_mco_paid` | MCO-paid amount absent where required |
| `err_void_no_icn` | Void encounter missing original ICN |
| `err_replacement_no_icn` | Replacement encounter missing original ICN |
| `err_charge_mismatch` | CLM02 total ≠ sum of service line charges |
| `err_invalid_dx_pointer` | Diagnosis pointer references nonexistent HI position |
| `err_bad_envelope` | ISA/IEA control number mismatch |
| `err_tpl_amounts_unbalanced` | TPL COB amounts inconsistent with claim total |

Scenarios must be extensible without modifying core generation logic.

### 837 EDI file generation requirements

- Separator characters (segment terminator, element separator,
  sub-element separator) must be configurable — not hardcoded. The
  validator detects them from ISA; the generator must exercise that
  detection path.
- Control numbers (ISA13, GS06, ST02) must be unique within a file,
  internally consistent, and seedable for reproducible runs.
- All loops and segments must appear in correct TR3 sequence.
- Each field mapping from encounter record to EDI segment/element must be
  documented in a code comment so the mapping is auditable.
- The generator must refuse to write an internally inconsistent encounter
  and must produce a descriptive error identifying the problem.
- Multi-encounter batch files must be supported.

---

## Capability 2: 837 Encounter Validation

### Validation layers

Four independently runnable layers. No layer depends on another having run
first (though they may share parsed output).

**Layer 1 — Envelope integrity**
- ISA/IEA, GS/GE, ST/SE control number pairs match
- Segment and transaction counts within each wrapper are accurate
- Separator characters detected from ISA — never hardcoded
- HL IDs and parent IDs form a valid, non-circular hierarchy
- Loop repetition counts within TR3 limits

**Layer 2 — X12 syntax (base TR3)**
- Required segments present in correct loop order
- Element values conform to data types, lengths, and allowed code sets per
  TR3
- Situational (conditional) element requirements evaluated correctly —
  each conditional rule must be its own named, individually testable
  function

**Layer 3 — DHS encounter business rules**
Derived exclusively from the retrieved companion guide documents. No rule
in this layer may be based on assumption or inference from other states'
guides. Every rule must carry a source comment citing the document and
section it came from. Starting checklist (extend from the actual retrieved
documents):
- MCO trading partner ID correctly placed in ISA06/GS02
- Provider UMPI present and correctly formatted in the appropriate
  identifier loops
- Atypical provider rule: TIN primary, G2 qualifier, UMPI secondary
- MCO-paid amount present where required
- Void/replacement encounters carry original ICN in required REF segment
- TPL COB loops present and correct when member has other insurance
- EPSDT/Teen Checkup CRC codes present and valid where applicable
- DHS mandatory values present in elements flagged in the DHS
  Requirements Value Column
- Write stubs with `# TODO: VERIFY AGAINST [document name/section]` for
  any rule that cannot be confirmed from the retrieved documents

**Layer 4 — Cross-field consistency**
- CLM02 total charge equals sum of all service line charge amounts
- MCO-paid amount does not exceed total charge
- TPL COB amounts internally consistent with claim-level amounts
- Service dates within statement coverage period (837I)
- Admission date precedes or equals discharge date (837I)
- Every diagnosis pointer in SV107/SV207 maps to an existing HI code
  position
- Void/replacement CLM05-3 code consistent with presence or absence of
  original ICN

### Validator output requirements

Every finding must include severity (error / warning / info), loop and
segment location with line number, description of what failed and the
correct condition, and which layer produced it. Output must support both
human-readable text and structured JSON. Exit codes must be CI-pipeline
compatible — confirm exact thresholds before implementing.

### Test requirements

- Every named error scenario must have a corresponding test asserting the
  expected finding appears.
- Every clean scenario must have a test asserting zero error-level
  findings.
- Each Layer 2 conditional rule must have at least one positive and one
  negative test.
- Tests use synthetic generator output as fixtures wherever possible.

---

## Capability 3: 999 and 835E Response Generation

### 999 generator requirements

- Input: an 837 encounter file, or the structured JSON validation report.
- Output: syntactically correct X12 999 with:
  - AK1/AK2/AK9 control numbers that trace directly back to
    ISA13/GS06/ST02 from the input file — not placeholder values
  - Real X12 error codes in IK3/IK4 when simulating rejections — no
    invented codes
  - Transaction set status consistent with validation findings
  - MN–ITS 999 file naming convention followed (based on ISA06 and GS08
    from the submitted file — confirm convention from retrieved
    documents)
- **Deterministic mode**: same named scenario always produces identical
  output
- **Simulation mode**: configurable outcome distribution across a batch
  for stress-testing downstream handling (e.g. accept rate, rejection
  reason mix)

### 835E generator requirements

- Input: an 837 encounter file plus an adjudication scenario (config file
  or CLI args).
- Output: syntactically correct X12 835 (005010X221A1) reflecting DHS
  encounter adjudication behavior, including:
  - BPR and TRN with realistic payment method codes and trace numbers
  - CLP with valid encounter claim payment status codes
  - CAS adjustments using CARC/RARC combinations sourced from the
    retrieved companion guides — do not invent pairings
  - SVC service-line detail with amounts balanced at claim and line level
  - Encounter-specific remark codes as used in DHS 835E outputs — source
    from the retrieved documents
- Same deterministic and simulation modes as the 999 generator.

### Named response scenarios (minimum required)

| Scenario | What it represents |
|---|---|
| `accept_all` | All encounters accepted, clean 999 + 835E |
| `reject_missing_umpi` | Encounters rejected for missing UMPI |
| `reject_bad_envelope` | Batch rejected at envelope level |
| `partial_accept` | Mixed batch with accepted and rejected encounters |
| `void_confirmed` | Void encounter acknowledged in 835E |
| `replacement_accepted` | Replacement accepted, original reversed |
| `zero_pay_accepted` | Zero-pay encounter accepted |

### Shared response generator requirements

- All control numbers, trading partner IDs, and dates configurable — no
  hardcoded values
- Generated files must pass Layer 1 of the validator
- Deterministic mode must produce identical output on repeated runs

---

## Working process

1. **First task**: fetch and save all documents listed in the Document
   Acquisition section. Populate `DOCUMENT_INDEX.md`. Do not proceed to any
   rule logic until at least the DHS 837 Encounter Companion Guide has been
   successfully retrieved.

2. **Before significant code for any capability**: propose your planned
   approach and module structure; wait for confirmation.

3. **Build incrementally in this order**:
   - Document acquisition and indexing
   - Synthetic data models and reference data pools
   - Named scenario generation and internal consistency checks
   - 837 EDI writer (encounter records → X12 files)
   - X12 parser (EDI text → structured representation)
   - Validator Layers 1, 2, and 4 (do not require companion guides)
   - Validator Layer 3 (DHS encounter rules — only after documents
     retrieved)
   - 999 generator
   - 835E generator
   - CLI wiring and integration tests

4. **Tests alongside code**: write tests for each module as it is built.
   Use synthetic generator output as fixtures.

5. **When a rule is ambiguous in the retrieved document**: write a stub,
   mark it with a `# TODO: AMBIGUOUS IN SOURCE — [document/section] —
   assumed behavior below` comment, and flag it in `KNOWN_LIMITATIONS.md`.

6. **Maintain `KNOWN_LIMITATIONS.md`**: implemented vs. stubbed vs.
   deferred. Update at the end of each working session.

---

## Disposition (as actually implemented)

This section was not part of the original spec; it is a brief, living
cross-reference added so this document stays useful as a checklist rather
than only a historical artifact.

- Every capability and named scenario above was implemented; see
  [`README.md`](../README.md) for the resulting project structure and CLI.
- Every place where the implementation had to resolve an ambiguity, fill a
  document gap, or deviate from a literal reading of this spec (e.g. the
  837/835 IG split for CLM05-3=7, UMPI format, the 999 file-naming
  convention, and 835E's structural source) is tracked in
  [`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md), cross-referenced to the
  exact source file and line.
- The architecture proposal that was reviewed and approved before
  implementation began (data models, libraries, project structure) is
  preserved in this Cursor workspace's plan history rather than duplicated
  here, to avoid two documents drifting out of sync.
