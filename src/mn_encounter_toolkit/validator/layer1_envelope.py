"""Layer 1: envelope integrity.

These rules are pure base-X12 envelope mechanics (ISA/GS/ST control-number
matching, segment/group counts) plus one DHS-specific rule (single
interchange per file). They do not require parsing any inner claim
content, which is why they are independent of -- and run before -- Layers
2-4 in validator/run.py.
"""

from __future__ import annotations

from mn_encounter_toolkit.edi.parser import ParsedDocument
from mn_encounter_toolkit.validator.findings import Finding
from mn_encounter_toolkit.validator.rule_registry import RuleRegistry

LAYER1 = RuleRegistry(layer=1)


@LAYER1.register("L1-ISA-PRESENT", "An ISA (interchange header) segment must be present.")
def rule_isa_present(doc: ParsedDocument) -> list[Finding]:
    if doc.first("ISA") is None:
        return [Finding("error", 1, "L1-ISA-PRESENT", "No ISA segment found in file.")]
    return []


@LAYER1.register("L1-IEA-PRESENT", "An IEA (interchange trailer) segment must be present.")
def rule_iea_present(doc: ParsedDocument) -> list[Finding]:
    if doc.first("IEA") is None:
        return [Finding("error", 1, "L1-IEA-PRESENT", "No IEA segment found in file.")]
    return []


@LAYER1.register(
    "L1-ONE-ISA-PER-FILE",
    "DHS requires exactly one ISA interchange per file.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.35 -- "
    "'PLEASE SEND ONE INTERCHANGE PER FILE UNTIL FURTHER NOTICE. IF YOU SEND MORE THAN ONE "
    "INTERCHANGE, THE ADDITIONAL INTERCHANGES MAY NOT BE PROCESSED.'",
)
def rule_one_isa_per_file(doc: ParsedDocument) -> list[Finding]:
    isas = doc.find("ISA")
    if len(isas) > 1:
        return [
            Finding(
                "error",
                1,
                "L1-ONE-ISA-PER-FILE",
                f"Found {len(isas)} ISA segments; DHS requires exactly one interchange per file.",
                segment_id="ISA",
                line_number=isas[1].line_number,
                source_citation="dhs_837_encounter_companion_guide.pdf p.35",
            )
        ]
    return []


@LAYER1.register("L1-ISA-IEA-CONTROL-MATCH", "ISA13 (interchange control number) must equal IEA02.")
def rule_isa_iea_control_match(doc: ParsedDocument) -> list[Finding]:
    isa, iea = doc.first("ISA"), doc.first("IEA")
    if isa is None or iea is None:
        return []
    isa13, iea02 = isa.el_str(13), iea.el_str(2)
    if isa13 != iea02:
        return [
            Finding(
                "error",
                1,
                "L1-ISA-IEA-CONTROL-MATCH",
                f"ISA13 ({isa13!r}) does not match IEA02 ({iea02!r}).",
                segment_id="IEA",
                line_number=iea.line_number,
            )
        ]
    return []


@LAYER1.register("L1-ISA13-FORMAT", "ISA13 must be a 9-digit, non-all-zero number.")
def rule_isa13_format(doc: ParsedDocument) -> list[Finding]:
    isa = doc.first("ISA")
    if isa is None:
        return []
    isa13 = isa.el_str(13)
    findings = []
    if not (isa13.isdigit() and len(isa13) == 9):
        findings.append(
            Finding(
                "error",
                1,
                "L1-ISA13-FORMAT",
                f"ISA13 ({isa13!r}) must be exactly 9 digits.",
                segment_id="ISA",
                line_number=isa.line_number,
            )
        )
    elif isa13 == "0" * 9:
        findings.append(
            Finding(
                "error",
                1,
                "L1-ISA13-FORMAT",
                "ISA13 must not be all zeros.",
                segment_id="ISA",
                line_number=isa.line_number,
            )
        )
    return findings


@LAYER1.register("L1-IEA-GROUP-COUNT", "IEA01 must equal the actual number of functional groups (GS) present.")
def rule_iea_group_count(doc: ParsedDocument) -> list[Finding]:
    iea = doc.first("IEA")
    if iea is None:
        return []
    actual = len(doc.find("GS"))
    try:
        declared = int(iea.el_str(1))
    except ValueError:
        return [
            Finding(
                "error", 1, "L1-IEA-GROUP-COUNT", f"IEA01 ({iea.el_str(1)!r}) is not numeric.",
                segment_id="IEA", line_number=iea.line_number,
            )
        ]
    if declared != actual:
        return [
            Finding(
                "error",
                1,
                "L1-IEA-GROUP-COUNT",
                f"IEA01 declares {declared} functional group(s) but {actual} GS segment(s) were found.",
                segment_id="IEA",
                line_number=iea.line_number,
            )
        ]
    return []


@LAYER1.register("L1-GS-GE-CONTROL-MATCH", "Each GS06 (group control number) must equal its paired GE02.")
def rule_gs_ge_control_match(doc: ParsedDocument) -> list[Finding]:
    gss, ges = doc.find("GS"), doc.find("GE")
    findings: list[Finding] = []
    if len(gss) != len(ges):
        findings.append(
            Finding(
                "error",
                1,
                "L1-GS-GE-CONTROL-MATCH",
                f"Found {len(gss)} GS segment(s) but {len(ges)} GE segment(s); cannot pair them.",
            )
        )
        return findings
    for gs, ge in zip(gss, ges):
        if gs.el_str(6) != ge.el_str(2):
            findings.append(
                Finding(
                    "error",
                    1,
                    "L1-GS-GE-CONTROL-MATCH",
                    f"GS06 ({gs.el_str(6)!r}) does not match GE02 ({ge.el_str(2)!r}).",
                    segment_id="GE",
                    line_number=ge.line_number,
                )
            )
    return findings


@LAYER1.register("L1-GE-ST-COUNT", "GE01 must equal the number of ST segments within that functional group.")
def rule_ge_st_count(doc: ParsedDocument) -> list[Finding]:
    indices = [(i, s) for i, s in enumerate(doc.segments) if s.seg_id in ("GS", "GE")]
    findings: list[Finding] = []
    open_gs_idx: int | None = None
    for idx, seg in indices:
        if seg.seg_id == "GS":
            open_gs_idx = idx
        elif seg.seg_id == "GE" and open_gs_idx is not None:
            st_count = sum(1 for s in doc.segments[open_gs_idx:idx] if s.seg_id == "ST")
            try:
                declared = int(seg.el_str(1))
            except ValueError:
                findings.append(
                    Finding("error", 1, "L1-GE-ST-COUNT", f"GE01 ({seg.el_str(1)!r}) is not numeric.",
                            segment_id="GE", line_number=seg.line_number)
                )
                open_gs_idx = None
                continue
            if declared != st_count:
                findings.append(
                    Finding(
                        "error",
                        1,
                        "L1-GE-ST-COUNT",
                        f"GE01 declares {declared} transaction set(s) but {st_count} ST segment(s) were found.",
                        segment_id="GE",
                        line_number=seg.line_number,
                    )
                )
            open_gs_idx = None
    return findings


@LAYER1.register("L1-ST-SE-CONTROL-MATCH", "Each ST02 (transaction set control number) must equal its paired SE02.")
def rule_st_se_control_match(doc: ParsedDocument) -> list[Finding]:
    sts, ses = doc.find("ST"), doc.find("SE")
    findings: list[Finding] = []
    if len(sts) != len(ses):
        findings.append(
            Finding(
                "error",
                1,
                "L1-ST-SE-CONTROL-MATCH",
                f"Found {len(sts)} ST segment(s) but {len(ses)} SE segment(s); cannot pair them.",
            )
        )
        return findings
    for st, se in zip(sts, ses):
        if st.el_str(2) != se.el_str(2):
            findings.append(
                Finding(
                    "error",
                    1,
                    "L1-ST-SE-CONTROL-MATCH",
                    f"ST02 ({st.el_str(2)!r}) does not match SE02 ({se.el_str(2)!r}).",
                    segment_id="SE",
                    line_number=se.line_number,
                )
            )
    return findings


@LAYER1.register("L1-SE-SEGMENT-COUNT", "SE01 must equal the actual number of segments between ST and SE, inclusive.")
def rule_se_segment_count(doc: ParsedDocument) -> list[Finding]:
    st_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "ST"]
    se_indices = [i for i, s in enumerate(doc.segments) if s.seg_id == "SE"]
    findings: list[Finding] = []
    for st_i, se_i in zip(st_indices, se_indices):
        actual = se_i - st_i + 1
        se = doc.segments[se_i]
        try:
            declared = int(se.el_str(1))
        except ValueError:
            findings.append(
                Finding("error", 1, "L1-SE-SEGMENT-COUNT", f"SE01 ({se.el_str(1)!r}) is not numeric.",
                        segment_id="SE", line_number=se.line_number)
            )
            continue
        if declared != actual:
            findings.append(
                Finding(
                    "error",
                    1,
                    "L1-SE-SEGMENT-COUNT",
                    f"SE01 declares {declared} segment(s) but {actual} were found between ST and SE.",
                    segment_id="SE",
                    line_number=se.line_number,
                )
            )
    return findings


@LAYER1.register(
    "L1-SEPARATORS-DISTINCT",
    "The four X12 delimiters (element, sub-element, repetition, segment terminator) must all be distinct single characters.",
)
def rule_separators_distinct(doc: ParsedDocument) -> list[Finding]:
    seps = doc.separators
    values = {
        seps.segment_terminator,
        seps.element_separator,
        seps.sub_element_separator,
        seps.repetition_separator,
    }
    if len(values) != 4:
        return [
            Finding(
                "error",
                1,
                "L1-SEPARATORS-DISTINCT",
                f"Detected delimiters are not all distinct: {seps}",
            )
        ]
    return []
