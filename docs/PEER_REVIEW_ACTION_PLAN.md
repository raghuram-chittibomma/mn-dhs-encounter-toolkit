# Peer Review Action Plan

> Tracker for findings from the external peer review (2026-07-01).
> Source: Claude Code review of `mn-dhs-encounter-toolkit`.
> Update status as items are resolved.

**Legend:** `[x]` done · `[ ]` open · `[~]` deferred / documented gap

---

## Phase 1 — Bugs & quick wins (priority)

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| P1-1 | Bug | 835E `_allocate_line_paid` rounding — last-bucket correction + balance assert | [x] | `gen_835e.py` |
| P1-2 | Bug | 999/835E `datetime.now()` breaks determinism — add `submission_time` | [x] | `gen_999.py`, `gen_835e.py` |
| P1-3 | Bug | Missing `L3-LINE-PAID-AMOUNT-REQUIRED-837I` (REF*9C) | [x] | `layer3_dhs_rules.py` |
| P1-4 | Bug | `err_*` scenarios bypass consistency guard (`err_missing_mco_paid`, `err_bad_envelope`) | [x] | `write_batch_checked` |
| P1-5 | Gap | Integration tests: per-scenario expected rule IDs | [x] | `test_pipeline.py` |
| P1-6 | Gap | Integration tests: generated 999/835E Layer-1-clean | [x] | `test_pipeline.py` |

---

## Phase 2 — Documentation & audit trail

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| P2-1 | Risk | `DOCUMENT_INDEX.md` "Used by" fields stale | [ ] | All four PDFs cite active code |
| P2-2 | — | Link this plan from `README.md` | [ ] | Optional |

---

## Phase 3 — Validator compliance hardening

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| P3-1 | Gap | `L3-SENDER-ID-MATCHES-SUBMITTER` (ISA06 vs GS02) | [x] | Companion guide p.35 |
| P3-2 | Gap | `L3-REFERRING-UMPI-REQUIRED` / `L3-RENDERING-UMPI-REQUIRED` | [x] | Loops 2310A/2310B |
| P3-3 | Gap | Atypical provider inverse validation | [~] | Deferred — synthetic toolkit scope |

---

## Phase 4 — 999 quality

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| P4-1 | Gap | Map validator findings → AK304 codes (not always `"8"`) | [ ] | `gen_999.py` |

---

## Phase 5 — Test coverage backlog

| ID | Severity | Item | Status | Notes |
|----|----------|------|--------|-------|
| P5-1 | Gap | Non-default separators through full validator pipeline | [ ] | Highest-risk edge case |
| P5-2 | Gap | Batch mixing void + original + replacement | [ ] | |
| P5-3 | Gap | Mixed 837P + 837I in one ISA | [ ] | |
| P5-4 | Gap | Empty file / max loop repetitions | [ ] | Lower priority |

---

## Accepted / no action (reviewer Pass or documented gap)

- Layer 3 source citations complete (§1.2)
- NPI Luhn implementation (§2.1)
- UMPI format assumed — `KNOWN_LIMITATIONS.md` (§2.2)
- Writer rejects inconsistent non-error encounters (§2.4)
- Layer 1 separator detection (§3.1)
- Layer 2 individually testable (§3.2)
- Void/replacement ICN rules (§3.8)
- Layer 4 Decimal charge balance (§3.9)
- Layers independent (§3.10)
- 999 AK1/AK2/AK9 trace (§4.1)
- CARC/RARC national codes (§5.1)
- 835E structural interpretation documented (§5.3)
- `KNOWN_LIMITATIONS.md` current (§7.1)
