# QA testing: this toolkit vs. DHS MN–ITS test

This document explains what the MN DHS Encounter Toolkit can and cannot
prove compared to submitting an 837 to **DHS's MN–ITS test environment** and
receiving real 999/835E responses.

Use this toolkit for **fast, local, repeatable pre-flight testing**. Use **DHS
test** for **authoritative integration sign-off** before production.

Related references:

- Rule catalog: [`VALIDATION_LAYERS.md`](VALIDATION_LAYERS.md)
- Document gaps and stubs: [`../KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md)
- Response generator design: [`ARCHITECTURE.md`](ARCHITECTURE.md) (999 / 835E section)

---

## At a glance

| | **This toolkit** | **DHS test (MN–ITS)** |
|---|---|---|
| **Connection** | Runs locally (CLI or web UI) | Real submission channel to DHS |
| **Data** | Synthetic members, providers, amounts | Real or DHS-issued test identities |
| **Responses** | Generated locally by this project's code | Produced by DHS after real processing |
| **Speed** | Instant | Depends on DHS test windows, queues, cutoffs |
| **Cost of failure** | Free iteration | May need DHS support, resubmission, partner coordination |

**Short version:** the toolkit is a **simulator + rule checker**. DHS test is the
**authoritative integration test**.

---

## Recommended QA workflow

```
Build / edit 837
    → Toolkit validate (Layers 1–4)
        → fix errors, document known warnings
    → Toolkit deterministic 999 / 835E preview (optional)
    → DHS MN–ITS test submit
        → compare real 999 / 835E to expectations
```

| Stage | Use toolkit | Use DHS test |
|-------|-------------|--------------|
| Developer / daily QA | Validate all four layers; preview deterministic 999 (L1–L2 scope) | |
| Pre-submission gate | Require clean Layer 1–3 (and Layer 4 unless waived) | |
| Integration sign-off | Compare artifacts only | **Required** |
| Downstream remit volume testing | Simulation mode for mixed paid/denied fixtures | Real 835E structure and remark codes |
| Go-live readiness | | Trading partner profile, test members, real responses |

---

## Major limitations vs. real DHS test

### 1. No real transport or MN–ITS workflow

The toolkit does not exercise:

- Trading partner enrollment or submitter credentials
- MN–ITS file upload (SFTP or other DHS-required transport)
- Interchange-level **TA1** rejections at the network layer
- DHS file naming, routing, or batch scheduling conventions (some details may
  live in DHS documents not yet fully retrieved — see
  [`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md))
- Operational issues: duplicate control numbers in DHS's system, resubmission
  windows, or how DHS treats `ISA15` test vs production on their side

A file can pass validation here and still fail before DHS parses your ST loops.

### 2. Local 999 responses are only a partial model

**Deterministic 999** re-runs **Layers 1 and 2 only** (envelope + base X12
syntax). It does **not** reflect:

- Layer 3 DHS business rules (UMPI, payer identity, MCO-paid amounts, etc.)
- Layer 4 cross-field consistency
- Any DHS-only edits not implemented in this project

So an 837 with DHS business-rule problems may receive a **local "accepted" 999**
while DHS would respond differently.

**Simulation 999** draws a seeded random accept / accept-with-errors / reject mix.
It is for **fixture generation**, not for predicting DHS behavior.

Known fidelity gaps in generated 999s:

- **AK302** (segment position within the transaction set) is hardcoded to `"1"` in
  places — not production-faithful (see
  [`PEER_REVIEW_ROUND2_ACTION_PLAN.md`](PEER_REVIEW_ROUND2_ACTION_PLAN.md) R2-C1)
- Some validator findings map to generic **AK304** code `"8"` when no explicit
  mapping exists

### 3. Local 835E is an interpretation, not confirmed DHS output

The 835E generator is this project's **reasonable construction**, not a confirmed
DHS encounter-835E specification:

- No DHS-specific 835E companion guide was fully available at build time
- **Deterministic mode** echoes adjudication data **already in the 837** (`AMT*D`,
  line-level paid refs) — it does not run DHS adjudication
- **Simulation mode** invents paid / partial / denied outcomes from a seeded RNG
- CARC/RARC pairs come from a small public pool, not a verified MN/DHS encounter
  list

DHS test returns remits from **their** encounter processing, which may differ in
segment mix, remark codes, payee grouping, or denial reasons.

### 4. Validation rules are not DHS's full edit engine

The toolkit implements a **curated subset** of rules traceable to retrieved
source documents (~52 rules across four layers). DHS likely runs additional
checks this project cannot model:

| Area | Toolkit | Likely at DHS |
|------|---------|---------------|
| Member exists and enrolled on date of service | Format check (8-digit ID) | Eligibility / enrollment database |
| Provider enrolled and in network | NPI Luhn + UMPI presence | Provider registry |
| Duplicate encounters | Not checked | Likely |
| Program-specific edits (PMAP, MSHO, etc.) | Partial via generator scenarios | Full payer logic |
| Historical void/replacement chains | ICN consistency (Layer 4) | May cross-check prior submissions |
| Rate and policy edits | Not modeled | Likely |

Documented gaps and stubs in the toolkit (see
[`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md)):

- **UMPI format** — required in the companion guide, but length/format unconfirmed;
  `L3-UMPI-FORMAT-STUB` produces no findings
- **CLM05-3 = `7` (replacement)** — flagged as a **warning** only; conflicts with
  the guide's own value table
- **Institutional DRG on 837I** — not written to output; unconfirmed in the
  encounter guide
- DHS landing-page PDFs (999 naming, encounter remark codes) were never fully
  retrieved

A **clean validation report here does not guarantee DHS acceptance**.

### 5. Synthetic data limits realism

The scenario lab generates **fake** members, providers, and paid amounts. DHS
test typically uses known test member IDs, enrolled providers, and trading
partner IDs tied to your MCO profile.

Errors such as "member not found," "provider not enrolled," or "invalid
submitter" often appear **only at DHS**, not locally.

### 6. No end-to-end operational proof

DHS test validates the production chain:

- File received → 999 returned → encounters loaded → 835E / remittance cycle
- Timing, idempotency, partial-batch handling
- How downstream systems ingest **real** DHS file formats and quirks

This toolkit cannot prove ETL, archive, or reconciliation jobs against **actual**
DHS artifacts.

### 7. Simulation mode can mislead if misused

**Simulation** modes for 999 and 835E are intentionally **decoupled** from the
837's real validity and amounts. Use them for stress testing and varied fixtures
— not to answer "will DHS respond this way?"

Only **deterministic** modes are logic-driven from input, and even those remain
local approximations (999: L1–L2 only; 835E: echo MCO-reported amounts).

---

## What this toolkit does better than DHS test

| Advantage | Why it matters for QA |
|-----------|----------------------|
| **Instant feedback** | Iterate on envelope, syntax, and companion-guide rules without waiting on DHS |
| **Repeatable fixtures** | Same `--seed` → same synthetic batch; suitable for CI and regression |
| **Edge cases on demand** | `err_*` scenarios, void/replacement, TPL, mixed 837P/837I |
| **Transparent rules** | Validation layers UI + cited Layer 3 findings |
| **Safe** | No real PII; no risk of polluting DHS test data |
| **Offline** | Works without VPN, credentials, or test-window access |

---

## Deterministic vs simulation (response pages)

| Mode | 999 | 835E |
|------|-----|------|
| **Deterministic** | Re-runs L1–L2 on the 837; AK segments reflect real envelope/syntax findings | Echoes MCO-paid amounts already in the 837 |
| **Simulation** | Seeded random accept / accept-with-errors / reject per transaction set | Seeded random paid / partial / denied per claim |

See the README `gen999` and `gen835e` sections for CLI flags (`--seed`,
`--outcome-weights`).

---

## Bottom line

| Passing here means… | Passing DHS test means… |
|---------------------|-------------------------|
| The file matches rules **implemented in this project** from public DHS/X12 docs, and local 999/835E generators can produce **plausible** responses | DHS **actually received, parsed, and processed** the submission the way production will |

Use this platform to catch structural and companion-guide issues early and to
train QA on rule IDs and scenarios. Reserve **DHS MN–ITS test** for final proof —
especially real identities, enrollment, transport, true adjudication outcomes, and
production-like 999/835E artifacts.
