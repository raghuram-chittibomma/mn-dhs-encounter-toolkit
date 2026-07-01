# Peer Review Round 2 — Action Plan

> Tracker for findings from the second external peer review (2026-07-01).
> First-round items are in [`PEER_REVIEW_ACTION_PLAN.md`](PEER_REVIEW_ACTION_PLAN.md) (all actionable items complete except deferred P3-3).

**Legend:** `[x]` done · `[ ]` open · `[~]` deferred / documented gap · `[!]` disputed / downgraded after code verification

**Overall verdict:** Sections 1–7 are **PASS** with one doc typo, one test gap, one optional validator gap, and one documented 999 limitation. Round 1 bug fixes (835E rounding, 999/835E determinism, 837I paid rule, `err_*` guard) are confirmed correct.

---

## Phase A — Quick fixes (do first)

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| R2-A1 | Doc | `DOCUMENT_INDEX.md:40` — repetition separator typo `]` → `[` | [x] | Matches `x12_core.py` default and `test_writer_parser.py` |
| R2-A2 | Hygiene | Add `ParsedSegment` to `layer3_dhs_rules.py` import | [x] | See **dispute note** below — not a runtime bug today |
| R2-A3 | Test | Negative test: `write_batch_checked([err_*])` without `allow_inconsistent=True` raises | [x] | `tests/unit/test_scenarios.py` (`err_bad_envelope`); also in `test_consistency.py` |

### Dispute note: R2-A2 (`ParsedSegment` NameError)

The reviewer flagged `_nm1_loops_missing_ref_g2` → `list[ParsedSegment]` as a **High** import-time `NameError`.

**Current code already has** `from __future__ import annotations` at `layer3_dhs_rules.py:11`, and the project requires **Python ≥ 3.11** (`pyproject.toml`). With postponed evaluation of annotations, `ParsedSegment` is **not** resolved at import time — Layer 3 tests pass today (141 tests).

**Recommendation:** Still add `ParsedSegment` to the import (one line). Low cost, clearer for readers/tools, and safe if `from __future__ import annotations` is ever removed. **Severity downgraded: Hygiene, not blocking.**

---

## Phase B — Validator gap (companion guide p.35–36)

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| R2-B1 | Gap | Validate ISA07/ISA08 (interchange receiver qualifier + id) | [x] | `L3-ISA-RECEIVER-FIXED` in `layer3_dhs_rules.py` |

**Proposed rule:** `L3-ISA-RECEIVER-FIXED` (or move to Layer 1 as envelope rule)

- ISA07 must be `30` (US Federal Tax Identification Number qualifier per guide envelope table)
- ISA08 (trailing spaces stripped) must equal `DHS_RECEIVER_FEIN_HYPHENATED` (`41-1674742`)
- Cross-check GS03 matches ISA08 without padding (mirror of `L3-SENDER-ID-MATCHES-SUBMITTER` pattern)
- Cite `dhs_837_encounter_companion_guide.pdf` p.35–36; add unit tests in `test_layer3_dhs_rules.py` (or `test_layer1_envelope.py` if placed in L1)
- Update `DOCUMENT_INDEX.md` rule list

**Effort:** ~1–2 hours. **Priority:** Medium — writer already emits correct values; this catches bad inbound files.

---

## Phase C — Documented gaps (no code change required)

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| R2-C1 | Gap | `gen_999.py` AK302 hardcoded to `"1"` | [~] | Segment position in transaction set not tracked; explicit comment at line 275. Log in `KNOWN_LIMITATIONS.md` if not already |
| R2-C2 | Gap | Atypical provider inverse validation | [~] | Carried from Round 1 P3-3 — out of synthetic-toolkit scope |
| R2-C3 | Gap | DHS landing-page accordion PDFs never fetched | [~] | Already in `KNOWN_LIMITATIONS.md` per Section 7 PASS |

**Optional enhancement (R2-C1):** Compute AK302 from segment index within ST..SE when building deterministic acks. Higher effort; only needed for production-faithful 999 fixtures.

---

## Confirmed PASS (no action)

These were re-verified and need no changes:

| Area | Finding |
|------|---------|
| **§1 Document traceability** | `DOCUMENT_INDEX.md` complete for all rule IDs including Phase 3 additions (except `]` typo) |
| **§2 Synthetic data** | `err_missing_mco_paid` encounter-level fix; `write_batch_checked` `err_*` guard by `scenario_name` |
| **§3 Validator** | `L3-LINE-PAID-AMOUNT-REQUIRED-837I`, sender ID, referring/rendering UMPI rules — logic correct |
| **§4 999** | Determinism fix; `ak304_for_finding` mapping + tests |
| **§5 835E** | `_split_by_weight` + balance assert; determinism fix |
| **§6 Tests** | Integration table items present; pipeline Layer-1 self-check on 999/835E |
| **§7 KNOWN_LIMITATIONS** | Current and cross-referenced |

---

## Suggested execution order

```
Phase A  (~30 min)   typo + import + one pytest
    ↓
Phase B  (~1–2 hr)  ISA07/ISA08 rule + tests + DOCUMENT_INDEX
    ↓
Phase C  (~15 min)  Add AK302 note to KNOWN_LIMITATIONS if missing; mark deferrals
    ↓
Push    (when ready)  all Round 1 + Round 2 commits to origin/main
```

---

## Test plan after implementation

```bash
source .venv/Scripts/activate
pytest -q                                    # expect 142+ after A3
pytest tests/unit/test_layer3_dhs_rules.py   # after B1
pytest tests/unit/test_scenarios.py          # after A3
```

---

## Changelog

| Date | Update |
|------|--------|
| 2026-07-01 | Plan created from second peer review feedback |
| 2026-07-01 | Phases A and B implemented (R2-A1–A3, R2-B1) |
