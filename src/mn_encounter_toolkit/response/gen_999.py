"""999 (Implementation Acknowledgment) generator.

SOURCE: mucg_999_ta1.pdf -- this one-page MN companion guide "adopts and
incorporates by reference ... the instructions ... in Appendix C.1 of the
ASC X12C/005010X231 Implementation Acknowledgment For Health Care
Insurance (999)" verbatim; it does not restate or customize the base IG.
Accordingly, this generator follows the *base* X12 005010X231 999
structure directly (AK1/AK2/AK3/AK4/AK5/AK9), with no DHS-specific
deviation to cite beyond "use the base IG as-is."

Two modes:
  - Deterministic: actually parses and runs Layers 1-2 (envelope + base
    syntax -- the two layers that are within a 999's scope; Layers 3-4 are
    DHS/cross-field business rules, which 999 does not speak to) against
    the input file and acknowledges exactly what was found.
  - Simulation: ignores the input file's actual validity and draws a
    randomly-weighted outcome from a seeded rng, for generating a varied
    set of 999 test fixtures on demand.
"""

from __future__ import annotations

import datetime as _dt
import random
from dataclasses import dataclass

from mn_encounter_toolkit.edi.parser import ParsedDocument, parse_segments
from mn_encounter_toolkit.edi.x12_core import DEFAULT_SEPARATORS, Separators, build_segment
from mn_encounter_toolkit.validator.findings import Finding
from mn_encounter_toolkit.validator.layer1_envelope import LAYER1
from mn_encounter_toolkit.validator.layer2_syntax import LAYER2

_SIMULATED_SEGMENT_ERROR_POOL = (
    ("CLM", "8"),  # 8 = Segment Has Data Element Errors
    ("HI", "8"),
    ("NM1", "8"),
    ("REF", "1"),  # 1 = Unrecognized Segment ID (simulated, not necessarily realistic)
    ("DTP", "8"),
    ("LX", "I6"),  # I6 = Implementation Dependent Segment Missing
    ("BHT", "3"),  # 3 = Required Segment Missing
)


# SOURCE: X12 005010X231 Implementation Acknowledgment, AK3-04 (IK304) --
# Implementation Segment Syntax Error Codes (Appendix C, Table 1).
_AK304_BY_RULE_ID: dict[str, str] = {
    "L1-ISA-PRESENT": "3",
    "L1-IEA-PRESENT": "3",
    "L1-ONE-ISA-PER-FILE": "5",
    "L2-BHT-PRESENT": "3",
    "L2-CLAIM-HAS-SERVICE-LINE": "I6",
    "L2-CLAIM-HAS-DIAGNOSIS": "I6",
}

# When a finding has no segment_id, infer the AK301 segment id from the rule.
_AK3_SEGMENT_BY_RULE_ID: dict[str, str] = {
    "L1-ISA-PRESENT": "ISA",
    "L1-IEA-PRESENT": "IEA",
    "L1-SEPARATORS-DISTINCT": "ISA",
    "L1-GS-GE-CONTROL-MATCH": "GS",
    "L1-ST-SE-CONTROL-MATCH": "ST",
    "L2-BHT-PRESENT": "BHT",
    "L2-CLAIM-HAS-SERVICE-LINE": "LX",
    "L2-CLAIM-HAS-DIAGNOSIS": "HI",
}


def ak304_for_finding(finding: Finding) -> str:
    """Map a Layer 1/2 validator finding to an AK304 segment syntax error code."""
    if finding.rule_id == "L2-CLM-EXACTLY-ONE-PER-CLAIM":
        if "has 0 CLM" in finding.message:
            return "I6"
        return "5"
    return _AK304_BY_RULE_ID.get(finding.rule_id, "8")


def ak3_segment_id_for_finding(finding: Finding) -> str | None:
    if finding.segment_id:
        return finding.segment_id
    return _AK3_SEGMENT_BY_RULE_ID.get(finding.rule_id)


def _segment_errors_from_findings(findings: list[Finding]) -> list[tuple[str, str]]:
    segment_errors: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        if finding.severity != "error":
            continue
        seg_id = ak3_segment_id_for_finding(finding)
        if not seg_id:
            continue
        code = ak304_for_finding(finding)
        key = (seg_id, code)
        if key in seen:
            continue
        seen.add(key)
        segment_errors.append(key)
    return segment_errors


@dataclass(frozen=True)
class TransactionAck:
    st_control_number: str
    transaction_set_ack_code: str  # AK501: A / E / R
    segment_errors: list[tuple[str, str]]  # (segment_id, AK304 error code)


def _ack_code_for(findings: list[Finding]) -> str:
    if any(f.severity == "error" for f in findings):
        return "R"
    if any(f.severity == "warning" for f in findings):
        return "E"
    return "A"


def _group_ack_code(transaction_acks: list[TransactionAck]) -> str:
    codes = {t.transaction_set_ack_code for t in transaction_acks}
    if "R" in codes:
        return "R"
    if "E" in codes:
        return "E"
    return "A"


def _segments_for_st(doc: ParsedDocument, st_index: int, se_index: int) -> list:
    return doc.segments[st_index : se_index + 1]


def build_deterministic_acks(original_text: str) -> tuple[ParsedDocument, dict[str, list[TransactionAck]]]:
    """Parse `original_text` and compute, per original GS group control
    number, the list of TransactionAck results (one per ST in that group),
    based on actual Layer 1 + Layer 2 findings."""
    doc = parse_segments(original_text)
    layer1_findings = LAYER1.run(doc)
    layer2_findings = LAYER2.run(doc)
    all_findings = layer1_findings + layer2_findings

    gs_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "GS"]
    ge_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "GE"]
    st_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "ST"]
    se_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "SE"]
    st_se_ranges = [
        (doc.segments[st_i].line_number, doc.segments[se_i].line_number)
        for st_i, se_i in zip(st_indices, se_indices)
    ]

    def is_global(finding: Finding) -> bool:
        # A finding is "global" (i.e. an envelope-level problem that taints
        # every transaction set in the file -- ISA/IEA/GS/GE control-number
        # mismatches, missing ISA/IEA, etc.) if it has no line number, or
        # its line number falls outside every known ST..SE range (which is
        # exactly where ISA/GS/GE/IEA segments live).
        if finding.line_number is None:
            return True
        return not any(lo <= finding.line_number <= hi for lo, hi in st_se_ranges)

    global_findings = [f for f in all_findings if is_global(f)]

    by_group: dict[str, list[TransactionAck]] = {}
    for gs_i, ge_i in zip(gs_indices, ge_indices):
        gs_control = doc.segments[gs_i].el_str(6)
        acks = []
        for st_i, se_i in zip(st_indices, se_indices):
            if not (gs_i < st_i < ge_i):
                continue
            st = doc.segments[st_i]
            se = doc.segments[se_i]
            scoped_findings = [
                f for f in all_findings if f.line_number is not None and st.line_number <= f.line_number <= se.line_number
            ]
            findings_for_st = global_findings + scoped_findings
            ack_code = _ack_code_for(findings_for_st)
            segment_errors = _segment_errors_from_findings(findings_for_st)
            acks.append(
                TransactionAck(
                    st_control_number=st.el_str(2),
                    transaction_set_ack_code=ack_code,
                    segment_errors=segment_errors,
                )
            )
        by_group[gs_control] = acks
    return doc, by_group


def build_simulated_acks(
    original_text: str, rng: random.Random, *, outcome_weights: dict[str, int] | None = None
) -> tuple[ParsedDocument, dict[str, list[TransactionAck]]]:
    doc = parse_segments(original_text)
    weights = outcome_weights or {"A": 70, "E": 20, "R": 10}
    outcomes = list(weights.keys())
    weight_values = list(weights.values())

    gs_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "GS"]
    ge_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "GE"]
    st_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "ST"]
    se_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "SE"]

    by_group: dict[str, list[TransactionAck]] = {}
    for gs_i, ge_i in zip(gs_indices, ge_indices):
        gs_control = doc.segments[gs_i].el_str(6)
        acks = []
        for st_i, se_i in zip(st_indices, se_indices):
            if not (gs_i < st_i < ge_i):
                continue
            st = doc.segments[st_i]
            ack_code = rng.choices(outcomes, weights=weight_values, k=1)[0]
            segment_errors = []
            if ack_code != "A":
                n_errors = rng.randint(1, 3)
                segment_errors = [
                    rng.choice(_SIMULATED_SEGMENT_ERROR_POOL) for _ in range(n_errors)
                ]
            acks.append(
                TransactionAck(
                    st_control_number=st.el_str(2),
                    transaction_set_ack_code=ack_code,
                    segment_errors=segment_errors,
                )
            )
        by_group[gs_control] = acks
    return doc, by_group


def render_999(
    original_doc: ParsedDocument,
    acks_by_group: dict[str, list[TransactionAck]],
    *,
    separators: Separators = DEFAULT_SEPARATORS,
    isa_control_number: int = 1,
    receiver_id: str = "411674742",
    submission_date: _dt.date | None = None,
    submission_time: str = "0800",
) -> str:
    """Render the 999 response text. `receiver_id` here is the *999's*
    sender -- i.e. whoever validated the original file (DHS/MN-ITS in
    production; this toolkit when self-checking)."""
    submission_date = submission_date or _dt.date.today()
    original_isa = original_doc.first("ISA")
    original_gs_list = original_doc.find("GS")

    segments: list[str] = []

    def add(*elements):
        segments.append(build_segment(separators, *elements))

    isa_cn = f"{isa_control_number:09d}"
    add(
        "ISA", "00", " " * 10, "00", " " * 10, "ZZ", receiver_id.ljust(15), "ZZ",
        (original_isa.el_str(6).strip() if original_isa else "").ljust(15),
        submission_date.strftime("%y%m%d"), submission_time,
        separators.repetition_separator, "00501", isa_cn, "0", "T", separators.sub_element_separator,
    )

    gs_cn = 1
    st_cn = 1
    for original_gs in original_gs_list:
        original_gs_control = original_gs.el_str(6)
        acks = acks_by_group.get(original_gs_control, [])
        add(
            "GS", "FA", receiver_id, original_gs.el_str(2),             submission_date.strftime("%Y%m%d"),
            submission_time, str(gs_cn), "X", "005010X231A1",
        )
        st_segments_start = len(segments)
        add("ST", "999", str(st_cn), "005010X231A1")
        add("AK1", original_gs.el_str(1), original_gs_control)
        for ack in acks:
            add("AK2", "837", ack.st_control_number)
            for seg_id, error_code in ack.segment_errors:
                # SOURCE: base X12 005010X231 999 IG, Appendix C -- AK304
                # is the Implementation Segment Syntax Error Code; AK301 is
                # the segment ID in error. AK303 (segment position in
                # transaction set) is intentionally omitted here -- this
                # toolkit does not track absolute segment position through
                # to the 999 generator, only the segment id.
                add("AK3", seg_id, "1", "", error_code)
            add("AK5", ack.transaction_set_ack_code)
        group_ack_code = _group_ack_code(acks) if acks else "A"
        add(
            "AK9",
            group_ack_code,
            str(len(acks)),
            str(len(acks)),
            str(sum(1 for a in acks if a.transaction_set_ack_code == "A")),
        )
        se_segment_count = len(segments) - st_segments_start + 1
        add("SE", str(se_segment_count), str(st_cn))
        add("GE", "1", str(gs_cn))
        gs_cn += 1
        st_cn += 1

    add("IEA", str(len(original_gs_list)), isa_cn)
    return "\n".join(segments) + "\n"


def generate_999_deterministic(original_text: str, **render_kwargs) -> str:
    doc, acks = build_deterministic_acks(original_text)
    return render_999(doc, acks, **render_kwargs)


def generate_999_simulated(
    original_text: str, rng: random.Random, *, outcome_weights: dict[str, int] | None = None, **render_kwargs
) -> str:
    doc, acks = build_simulated_acks(original_text, rng, outcome_weights=outcome_weights)
    return render_999(doc, acks, **render_kwargs)
