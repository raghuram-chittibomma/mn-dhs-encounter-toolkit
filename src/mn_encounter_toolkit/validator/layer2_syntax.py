"""Layer 2: base X12/TR3 syntax -- rules that come from the underlying X12
005010X222A1/X223A2 implementation guides themselves, not from DHS. None of
these rules carry a DHS source_citation; that is what distinguishes them
from Layer 3.
"""

from __future__ import annotations

import re

from mn_encounter_toolkit.edi.parser import ParsedDocument
from mn_encounter_toolkit.identifiers.npi import is_valid_npi
from mn_encounter_toolkit.validator.findings import Finding
from mn_encounter_toolkit.validator.rule_registry import RuleRegistry

LAYER2 = RuleRegistry(layer=2)

_MONEY_RE = re.compile(r"^\d+\.\d{2}$")
_DATE8_RE = re.compile(r"^\d{8}$")


def _valid_date8(value: str) -> bool:
    if not _DATE8_RE.match(value):
        return False
    try:
        from datetime import date

        date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
        return True
    except ValueError:
        return False


@LAYER2.register("L2-ST01-VALUE", "ST01 must be '837' (Health Care Claim transaction set identifier).")
def rule_st01_value(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for st in doc.find("ST"):
        if st.el_str(1) != "837":
            findings.append(
                Finding("error", 2, "L2-ST01-VALUE", f"ST01 must be '837', got {st.el_str(1)!r}.",
                        segment_id="ST", line_number=st.line_number)
            )
    return findings


@LAYER2.register("L2-BHT-PRESENT", "Each transaction set must include exactly one BHT segment.")
def rule_bht_present(doc: ParsedDocument) -> list[Finding]:
    sts = doc.find("ST")
    bhts = doc.find("BHT")
    if len(bhts) < len(sts):
        return [
            Finding(
                "error", 2, "L2-BHT-PRESENT",
                f"Found {len(sts)} ST segment(s) but only {len(bhts)} BHT segment(s).",
            )
        ]
    return []


@LAYER2.register("L2-CLM-EXACTLY-ONE-PER-CLAIM", "Each claim block must contain exactly one CLM segment.")
def rule_clm_exactly_one(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        clms = block.find("CLM")
        if len(clms) != 1:
            findings.append(
                Finding(
                    "error",
                    2,
                    "L2-CLM-EXACTLY-ONE-PER-CLAIM",
                    f"Claim under subscriber HL {block.hl_subscriber_id} has {len(clms)} CLM segments (expected 1).",
                    segment_id="CLM",
                )
            )
    return findings


@LAYER2.register("L2-CLM02-MONEY-FORMAT", "CLM02 (total claim charge amount) must be a non-negative decimal with exactly 2 places.")
def rule_clm02_money_format(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for clm in doc.find("CLM"):
        value = clm.el_str(2)
        if not _MONEY_RE.match(value):
            findings.append(
                Finding(
                    "error", 2, "L2-CLM02-MONEY-FORMAT",
                    f"CLM02 ({value!r}) is not a valid non-negative decimal amount with 2 places.",
                    segment_id="CLM", line_number=clm.line_number,
                )
            )
    return findings


@LAYER2.register("L2-AMT02-MONEY-FORMAT", "AMT02 (monetary amount) must be a non-negative decimal with exactly 2 places.")
def rule_amt02_money_format(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for amt in doc.find("AMT"):
        value = amt.el_str(2)
        if not _MONEY_RE.match(value):
            findings.append(
                Finding(
                    "error", 2, "L2-AMT02-MONEY-FORMAT",
                    f"AMT02 ({value!r}) under qualifier {amt.el_str(1)!r} is not a valid non-negative "
                    "decimal amount with 2 places.",
                    segment_id="AMT", line_number=amt.line_number,
                )
            )
    return findings


@LAYER2.register("L2-DTP-DATE8-FORMAT", "DTP segments using the D8 qualifier must carry a valid CCYYMMDD calendar date.")
def rule_dtp_date8_format(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for dtp in doc.find("DTP"):
        if dtp.el_str(2) == "D8":
            value = dtp.el_str(3)
            if not _valid_date8(value):
                findings.append(
                    Finding(
                        "error", 2, "L2-DTP-DATE8-FORMAT",
                        f"DTP03 ({value!r}) is not a valid CCYYMMDD date.",
                        segment_id="DTP", line_number=dtp.line_number,
                    )
                )
    return findings


@LAYER2.register("L2-NM1-ENTITY-TYPE-QUALIFIER", "NM102 (entity type qualifier) must be '1' (person) or '2' (non-person entity).")
def rule_nm1_entity_type_qualifier(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for nm1 in doc.find("NM1"):
        value = nm1.el_str(2)
        if value not in ("1", "2"):
            findings.append(
                Finding(
                    "error", 2, "L2-NM1-ENTITY-TYPE-QUALIFIER",
                    f"NM102 ({value!r}) must be '1' or '2' (NM101={nm1.el_str(1)!r}).",
                    segment_id="NM1", line_number=nm1.line_number,
                )
            )
    return findings


@LAYER2.register("L2-HL-LEVEL-CODE-KNOWN", "HL03 (hierarchical level code) must be a value used by the 837 IG (here: '20' or '22').")
def rule_hl_level_code_known(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for hl in doc.find("HL"):
        value = hl.el_str(3)
        if value not in ("20", "22"):
            findings.append(
                Finding(
                    "error", 2, "L2-HL-LEVEL-CODE-KNOWN",
                    f"HL03 ({value!r}) is not a recognized hierarchical level code.",
                    segment_id="HL", line_number=hl.line_number,
                )
            )
    return findings


@LAYER2.register("L2-CLAIM-HAS-SERVICE-LINE", "Each claim must have at least one service line (LX).")
def rule_claim_has_service_line(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if not block.find("LX"):
            findings.append(
                Finding(
                    "error", 2, "L2-CLAIM-HAS-SERVICE-LINE",
                    f"Claim under subscriber HL {block.hl_subscriber_id} has no LX (service line) segments.",
                )
            )
    return findings


@LAYER2.register("L2-CLAIM-HAS-DIAGNOSIS", "Each claim must have at least one HI (diagnosis) segment.")
def rule_claim_has_diagnosis(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if not block.find("HI"):
            findings.append(
                Finding(
                    "error", 2, "L2-CLAIM-HAS-DIAGNOSIS",
                    f"Claim under subscriber HL {block.hl_subscriber_id} has no HI (diagnosis) segments.",
                )
            )
    return findings


@LAYER2.register(
    "L2-NPI-CHECK-DIGIT-VALID",
    "Any NM109 submitted under the XX (NPI) qualifier must pass the standard CMS Luhn check-digit "
    "algorithm. This is a base CMS/NPPES rule, not DHS-specific -- it belongs in Layer 2.",
)
def rule_npi_check_digit_valid(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for nm1 in doc.find("NM1"):
        if nm1.el_str(8) == "XX":
            npi = nm1.el_str(9)
            if npi and not is_valid_npi(npi):
                findings.append(
                    Finding(
                        "error", 2, "L2-NPI-CHECK-DIGIT-VALID",
                        f"NM109 ({npi!r}) is not a valid NPI (fails the Luhn check digit algorithm).",
                        segment_id="NM1", line_number=nm1.line_number,
                    )
                )
    return findings


@LAYER2.register("L2-DIAGNOSIS-CODE-NO-DECIMAL", "Diagnosis (HI) industry codes must not contain a decimal point.")
def rule_diagnosis_code_no_decimal(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for hi in doc.find("HI"):
        composite = hi.composite(1)
        if len(composite) >= 2 and "." in composite[1]:
            findings.append(
                Finding(
                    "error", 2, "L2-DIAGNOSIS-CODE-NO-DECIMAL",
                    f"Diagnosis code {composite[1]!r} must not contain a decimal point.",
                    segment_id="HI", line_number=hi.line_number,
                )
            )
    return findings
