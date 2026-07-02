"""Layer 3: DHS encounter-specific business rules.

Every rule function below carries a SOURCE comment citing the exact
page/loop/segment of dhs_837_encounter_companion_guide.pdf it enforces.
Rules that could not be fully confirmed from the retrieved documents are
marked "# TODO: VERIFY AGAINST ..." or "# TODO: AMBIGUOUS IN SOURCE ..." and
are cross-referenced in KNOWN_LIMITATIONS.md, per the spec's requirement
that unconfirmed rules be flagged rather than guessed at silently.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from mn_encounter_toolkit.edi.parser import ClaimBlock, ParsedDocument, ParsedSegment
from mn_encounter_toolkit.models.core import DHS_PAYER_ID, DHS_PAYER_NAME, DHS_RECEIVER_FEIN_HYPHENATED
from mn_encounter_toolkit.validator.findings import Finding
from mn_encounter_toolkit.validator.rule_registry import RuleRegistry

LAYER3 = RuleRegistry(layer=3)


def _claim_type(block: ClaimBlock) -> str:
    return "837I" if block.find("SV2") else "837P"


def _to_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _nm1_loops_missing_ref_g2(block: ClaimBlock, entity_code: str) -> list[ParsedSegment]:
    """Return NM1 segments in the claim loop whose immediate following
    segments (until the next NM1/LX/CLM/HL) lack a populated REF*G2."""
    missing: list[ParsedSegment] = []
    claim_segs = block.claim_segments
    for i, seg in enumerate(claim_segs):
        if seg.seg_id != "NM1" or seg.el_str(1) != entity_code:
            continue
        has_g2 = False
        for follow in claim_segs[i + 1 :]:
            if follow.seg_id in ("NM1", "LX", "CLM", "HL"):
                break
            if follow.seg_id == "REF" and follow.el_str(1) == "G2" and follow.el_str(2).strip():
                has_g2 = True
                break
        if not has_g2:
            missing.append(seg)
    return missing


def _first_lx_index(block: ClaimBlock) -> int | None:
    for i, seg in enumerate(block.claim_segments):
        if seg.seg_id == "LX":
            return i
    return None


def _claim_header_segments(block: ClaimBlock) -> list[ParsedSegment]:
    idx = _first_lx_index(block)
    if idx is None:
        return block.claim_segments
    return block.claim_segments[:idx]


def _line_groups(block: ClaimBlock) -> list[list[ParsedSegment]]:
    groups: list[list[ParsedSegment]] = []
    current: list[ParsedSegment] = []
    for seg in block.claim_segments:
        if seg.seg_id == "LX":
            if current:
                groups.append(current)
            current = [seg]
        elif current:
            current.append(seg)
    if current:
        groups.append(current)
    return groups


def _refs_in_line_groups(block: ClaimBlock, qualifier: str) -> list[ParsedSegment]:
    out: list[ParsedSegment] = []
    for group in _line_groups(block):
        out.extend(s for s in group if s.seg_id == "REF" and s.el_str(1) == qualifier)
    return out


@LAYER3.register(
    "L3-BILLING-TIN-REQUIRED",
    "Billing provider (Loop 2010AA) must carry a tax id via REF*EI, regardless of NPI presence.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.14 (837P) / p.38 (837I) -- "
    "Loop 2010AA REF, REQ=Y: 'REF01=EI PROVIDERS EMPLOYER IDENTIFICATION NUMBER'.",
)
def rule_billing_tin_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        refs_ei = [r for r in block.find_in_billing("REF") if r.el_str(1) == "EI"]
        if not refs_ei or not refs_ei[0].el_str(2):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-BILLING-TIN-REQUIRED",
                    f"Billing provider for claim under subscriber HL {block.hl_subscriber_id} is "
                    "missing a REF*EI tax identification number.",
                    segment_id="REF",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.14/p.38",
                )
            )
    return findings


@LAYER3.register(
    "L3-BILLING-UMPI-REQUIRED",
    "Billing provider (Loop 2010AA) must carry the DHS UMPI as a secondary identifier via REF*G2.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.17 (837P) / p.40 (837I) -- "
    "Loop 2010AA REF, 'REF01=G2 ... REF02 = BILLING PROVIDER SECONDARY IDENTIFIER (DHS UMPI NUMBER)'.",
)
def rule_billing_umpi_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        refs_g2 = [r for r in block.find_in_billing("REF") if r.el_str(1) == "G2"]
        if not refs_g2 or not refs_g2[0].el_str(2):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-BILLING-UMPI-REQUIRED",
                    f"Billing provider for claim under subscriber HL {block.hl_subscriber_id} is "
                    "missing a REF*G2 (UMPI) secondary identifier.",
                    segment_id="REF",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.17/p.40",
                )
            )
    return findings


@LAYER3.register(
    "L3-SERVICE-FACILITY-UMPI-REQUIRED",
    "When a service facility location loop (NM1*77) is present, it must carry REF*G2 (UMPI).",
    source_citation="dhs_837_encounter_companion_guide.pdf p.22 (837P) / p.52 (837I) -- "
    "service facility loop REF*G2 (C1).",
)
def rule_service_facility_umpi_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        for nm1 in _nm1_loops_missing_ref_g2(block, "77"):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SERVICE-FACILITY-UMPI-REQUIRED",
                    f"Service facility (NM1*77) for claim under subscriber HL "
                    f"{block.hl_subscriber_id} is missing a REF*G2 (UMPI) secondary identifier.",
                    segment_id="NM1",
                    line_number=nm1.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.22/p.52",
                )
            )
    return findings


@LAYER3.register(
    "L3-REFERRING-UMPI-REQUIRED",
    "When a referring provider loop (NM1*DN) is present, it must carry REF*G2 (UMPI) as a secondary identifier.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.21 (837P) -- Loop 2310A REF: "
    "'REF01=G2 ... REF02 = REFERRING PROVIDER SECONDARY IDENTIFIER (DHS UMPI NUMBER)'.",
)
def rule_referring_umpi_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        for nm1 in _nm1_loops_missing_ref_g2(block, "DN"):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-REFERRING-UMPI-REQUIRED",
                    f"Referring provider (NM1*DN) for claim under subscriber HL {block.hl_subscriber_id} "
                    "is missing a REF*G2 (UMPI) secondary identifier.",
                    segment_id="NM1",
                    line_number=nm1.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.21",
                )
            )
    return findings


@LAYER3.register(
    "L3-RENDERING-UMPI-REQUIRED",
    "When a distinct rendering provider loop (NM1*82) is present, it must carry REF*G2 (UMPI) as a secondary identifier.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.22 (837P) -- Loop 2310B REF: "
    "'REF01=G2 ... REF02 = RENDERING PROVIDER SECONDARY IDENTIFIER (DHS UMPI NUMBER)'.",
)
def rule_rendering_umpi_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        for nm1 in _nm1_loops_missing_ref_g2(block, "82"):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-RENDERING-UMPI-REQUIRED",
                    f"Rendering provider (NM1*82) for claim under subscriber HL {block.hl_subscriber_id} "
                    "is missing a REF*G2 (UMPI) secondary identifier.",
                    segment_id="NM1",
                    line_number=nm1.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.22",
                )
            )
    return findings


@LAYER3.register(
    "L3-MCO-ADJUDICATION-REQUIRED",
    "Loop 2320's mandatory first occurrence (the MCO reporting its own adjudication) must be present "
    "on every claim, independent of whether TPL is also present.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.23 -- "
    "'2320 ... THIS LOOP IS REQUIRED -- THE FIRST OCCURRENCE MUST CONTAIN INFORMATION FOR THE MCO "
    "AS THE PRIMARY/SECONDARY PAYER.'",
)
def rule_mco_adjudication_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        amts_d = [a for a in block.find("AMT") if a.el_str(1) == "D"]
        if not amts_d:
            clm = block.clm()
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-MCO-ADJUDICATION-REQUIRED",
                    f"Claim {clm.el_str(1) if clm else block.hl_subscriber_id!r} is missing the "
                    "mandatory first occurrence of loop 2320 (MCO's own adjudication, AMT*D).",
                    segment_id="AMT",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.23",
                )
            )
    return findings


@LAYER3.register(
    "L3-PAYER-NAME-FIXED",
    "Loop 2010BB payer must always be DHS itself: NM103='MN DEPT OF HUMAN SERVICES', NM109=411674742.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.15-16 (837P) / p.40 (837I) -- "
    "Loop 2010BB NM1: 'NM103 ... MN DEPT OF HUMAN SERVICES', 'NM109 ... 411674742 DHS PAYER ID'.",
)
def rule_payer_name_fixed(doc: ParsedDocument) -> list[Finding]:
    # Only the FIRST NM1*PR per claim is the true Loop 2010BB payer. Later
    # NM1*PR occurrences belong to loop 2320/2330B (the MCO's own
    # adjudication "payer" copy, and -- for TPL claims -- the actual third
    # party payer), which are legitimately NOT DHS. See
    # models/encounter.py TPLPayer / MCOAdjudication docstrings.
    findings = []
    for block in doc.claim_blocks():
        payer_nm1s = [n for n in block.find("NM1") if n.el_str(1) == "PR"]
        if not payer_nm1s:
            continue
        nm1 = payer_nm1s[0]
        if nm1.el_str(3) != DHS_PAYER_NAME or nm1.el_str(9) != DHS_PAYER_ID:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-PAYER-NAME-FIXED",
                    f"Payer (Loop 2010BB) must be {DHS_PAYER_NAME!r}/{DHS_PAYER_ID!r}, got "
                    f"{nm1.el_str(3)!r}/{nm1.el_str(9)!r}.",
                    segment_id="NM1",
                    line_number=nm1.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.15-16/p.40",
                )
            )
    return findings


@LAYER3.register(
    "L3-RECEIVER-FIXED",
    "Loop 1000B receiver must be DHS: NM101=40, NM108=46, NM109=411674742.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.13 (837P) / p.37 (837I) -- "
    "Loop 1000B NM1: 'NM109 ... 411674742 RECEIVER ID'.",
)
def rule_receiver_fixed(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for nm1 in doc.find("NM1"):
        if nm1.el_str(1) == "40":
            if nm1.el_str(8) != "46" or nm1.el_str(9) != DHS_PAYER_ID:
                findings.append(
                    Finding(
                        "error",
                        3,
                        "L3-RECEIVER-FIXED",
                        f"Receiver (Loop 1000B) NM108/NM109 must be '46'/{DHS_PAYER_ID!r}, got "
                        f"{nm1.el_str(8)!r}/{nm1.el_str(9)!r}.",
                        segment_id="NM1",
                        line_number=nm1.line_number,
                        source_citation="dhs_837_encounter_companion_guide.pdf p.13/p.37",
                    )
                )
    return findings


@LAYER3.register(
    "L3-SUBMITTER-TRADING-PARTNER-QUALIFIER",
    "Loop 1000A submitter (the MCO) must use NM108='46' (Trading Partner ID qualifier).",
    source_citation="dhs_837_encounter_companion_guide.pdf p.13 (837P) / p.37 (837I) -- "
    "Loop 1000A NM1: 'NM108 ... 46 TRADING PARTNER ID'.",
)
def rule_submitter_trading_partner_qualifier(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for nm1 in doc.find("NM1"):
        if nm1.el_str(1) == "41" and nm1.el_str(8) != "46":
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SUBMITTER-TRADING-PARTNER-QUALIFIER",
                    f"Submitter (Loop 1000A) NM108 must be '46', got {nm1.el_str(8)!r}.",
                    segment_id="NM1",
                    line_number=nm1.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.13/p.37",
                )
            )
    return findings


@LAYER3.register(
    "L3-SENDER-ID-MATCHES-SUBMITTER",
    "ISA06 (interchange sender id, trailing spaces stripped) must equal GS02 and the Loop 1000A submitter id (NM1*41 NM109).",
    source_citation="dhs_837_encounter_companion_guide.pdf p.35-36, Envelope Information -- "
    "'ISA06 ... MUST CHANGE TO THE 10-DIGIT ... NPI OR ... UMPI FOLLOWED BY 5 TRAILING SPACES' and "
    "'GS02 ... MUST MATCH THE NUMBER IN ISA06 WITHOUT THE TRAILING SPACES.'",
)
def rule_sender_id_matches_submitter(doc: ParsedDocument) -> list[Finding]:
    findings: list[Finding] = []
    isa = doc.first("ISA")
    if isa is None:
        return findings
    isa06 = isa.el_str(6).rstrip()
    citation = "dhs_837_encounter_companion_guide.pdf p.35-36"

    for gs in doc.find("GS"):
        gs02 = gs.el_str(2).rstrip()
        if isa06 != gs02:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SENDER-ID-MATCHES-SUBMITTER",
                    f"ISA06 ({isa06!r}) does not match GS02 ({gs02!r}).",
                    segment_id="GS",
                    line_number=gs.line_number,
                    source_citation=citation,
                )
            )

    submitter = next((n for n in doc.find("NM1") if n.el_str(1) == "41"), None)
    if submitter is not None:
        nm109 = submitter.el_str(9).strip()
        if nm109 and isa06 != nm109:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SENDER-ID-MATCHES-SUBMITTER",
                    f"ISA06 ({isa06!r}) does not match Loop 1000A submitter NM109 ({nm109!r}).",
                    segment_id="NM1",
                    line_number=submitter.line_number,
                    source_citation=citation,
                )
            )
    return findings


@LAYER3.register(
    "L3-ISA-RECEIVER-FIXED",
    "Interchange receiver (ISA07/ISA08) must use qualifier 30 and the DHS hyphenated FEIN; GS03 must match ISA08 without padding.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.35-36, Envelope Information -- "
    "'ISA07 ... 30 US FEDERAL TAX IDENTIFICATION NUMBER' and "
    "'ISA08 ... 41-1674742 ... FOLLOWED BY 5 TRAILING SPACES'; GS03 must match ISA08 without padding.",
)
def rule_isa_receiver_fixed(doc: ParsedDocument) -> list[Finding]:
    findings: list[Finding] = []
    isa = doc.first("ISA")
    if isa is None:
        return findings
    citation = "dhs_837_encounter_companion_guide.pdf p.35-36"
    isa07 = isa.el_str(7)
    isa08 = isa.el_str(8).rstrip()

    if isa07 != "30":
        findings.append(
            Finding(
                "error",
                3,
                "L3-ISA-RECEIVER-FIXED",
                f"ISA07 must be '30' (US Federal Tax Identification Number qualifier), got {isa07!r}.",
                segment_id="ISA",
                line_number=isa.line_number,
                source_citation=citation,
            )
        )
    if isa08 != DHS_RECEIVER_FEIN_HYPHENATED:
        findings.append(
            Finding(
                "error",
                3,
                "L3-ISA-RECEIVER-FIXED",
                f"ISA08 ({isa08!r}) must be {DHS_RECEIVER_FEIN_HYPHENATED!r} (trailing spaces stripped).",
                segment_id="ISA",
                line_number=isa.line_number,
                source_citation=citation,
            )
        )

    for gs in doc.find("GS"):
        gs03 = gs.el_str(3).rstrip()
        if isa08 and gs03 != isa08:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-ISA-RECEIVER-FIXED",
                    f"ISA08 ({isa08!r}) does not match GS03 ({gs03!r}).",
                    segment_id="GS",
                    line_number=gs.line_number,
                    source_citation=citation,
                )
            )
    return findings


@LAYER3.register(
    "L3-MEMBER-ID-EIGHT-DIGITS",
    "Subscriber (member) ID at Loop 2010BA NM109 must be the DHS-assigned eight-digit member id.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.15 (837P) / p.39 (837I) -- "
    "'NM109 ... DHS ASSIGNED EIGHT DIGIT MEMBER ID'.",
)
def rule_member_id_eight_digits(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        nm1s = [n for n in block.find("NM1") if n.el_str(1) == "IL" and n.el_str(8) == "MI"]
        for nm1 in nm1s[:1]:  # first IL/MI NM1 per claim is the 2010BA subscriber, not the 2320 COB copy
            member_id = nm1.el_str(9)
            if not (member_id.isdigit() and len(member_id) == 8):
                findings.append(
                    Finding(
                        "error",
                        3,
                        "L3-MEMBER-ID-EIGHT-DIGITS",
                        f"Member ID ({member_id!r}) must be exactly 8 digits.",
                        segment_id="NM1",
                        line_number=nm1.line_number,
                        source_citation="dhs_837_encounter_companion_guide.pdf p.15/p.39",
                    )
                )
    return findings


@LAYER3.register(
    "L3-EPSDT-NU-WHEN-NO-REFERRAL",
    "When CRC02 (was a referral given) is 'N', CRC03 must be 'NU'.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.19 (837P) / p.45 (837I) -- "
    "'NU ... NOT USED. THIS CONDITION INDICATOR MUST BE USED WHEN THE SUBMITTER ANSWERS \"N\" IN CRC02.'",
)
def rule_epsdt_nu_when_no_referral(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for crc in doc.find("CRC"):
        if crc.el_str(1) == "ZZ" and crc.el_str(2) == "N" and crc.el_str(3) != "NU":
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-EPSDT-NU-WHEN-NO-REFERRAL",
                    f"CRC02='N' requires CRC03='NU', got {crc.el_str(3)!r}.",
                    segment_id="CRC",
                    line_number=crc.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.19/p.45",
                )
            )
    return findings


@LAYER3.register(
    "L3-VOID-REF-F8-ONLY",
    "REF*F8 (original reference number) must only appear on void claims (CLM05-3=8).",
    source_citation="dhs_837_encounter_companion_guide.pdf p.19 (837P) / p.43 (837I) -- "
    "'REF02 ... USED WHEN CLM05-3 IS 8-VOID. THIS IS FOR VOID CLAIM USAGE ONLY.'",
)
def rule_void_ref_f8_only(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        freq = clm.composite(5)
        freq_code = freq[2] if len(freq) >= 3 else None
        ref_f8 = [r for r in block.find("REF") if r.el_str(1) == "F8"]
        if ref_f8 and freq_code != "8":
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-VOID-REF-F8-ONLY",
                    f"REF*F8 is present but CLM05-3 is {freq_code!r}, not '8' (void-only usage).",
                    segment_id="REF",
                    line_number=ref_f8[0].line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.19/p.43",
                )
            )
    return findings


@LAYER3.register(
    "L3-DIAGNOSIS-PRINCIPAL-QUALIFIER",
    "The first HI segment on a claim (the principal diagnosis) must use code-list qualifier ABK.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.20 (837P) / p.45 (837I) -- "
    "'HI01-1 ... ABK ICD-10-CM PRINCIPAL DIAGNOSIS'.",
)
def rule_diagnosis_principal_qualifier(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        his = block.find("HI")
        if not his:
            continue
        qualifier = his[0].composite(1)[0] if his[0].composite(1) else ""
        if qualifier != "ABK":
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-DIAGNOSIS-PRINCIPAL-QUALIFIER",
                    f"First HI segment must use qualifier 'ABK' (principal diagnosis), got {qualifier!r}.",
                    segment_id="HI",
                    line_number=his[0].line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.20/p.45",
                )
            )
    return findings


@LAYER3.register(
    "L3-DIAGNOSIS-SUBSEQUENT-QUALIFIER",
    "Every HI segment after the first (non-principal diagnoses) must use code-list qualifier ABF.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.20 (837P) / p.47 (837I) -- "
    "'HI01-1 ... ABF ICD-10-CM OTHER DIAGNOSIS'.",
)
def rule_diagnosis_subsequent_qualifier(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        his = block.find("HI")
        for hi in his[1:]:
            qualifier = hi.composite(1)[0] if hi.composite(1) else ""
            if qualifier != "ABF":
                findings.append(
                    Finding(
                        "error",
                        3,
                        "L3-DIAGNOSIS-SUBSEQUENT-QUALIFIER",
                        f"Non-principal HI segment must use qualifier 'ABF', got {qualifier!r}.",
                        segment_id="HI",
                        line_number=hi.line_number,
                        source_citation="dhs_837_encounter_companion_guide.pdf p.20/p.47",
                    )
                )
    return findings


@LAYER3.register(
    "L3-837I-CL1-REQUIRED",
    "837I claims must include a CL1 institutional claim code segment in loop 2300.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.43 (837I) -- CL1 segment REQ=Y "
    "(CL101 admission type, CL103 patient status; CL102 admission source is C1).",
)
def rule_837i_cl1_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        if not block.find("CL1"):
            clm = block.clm()
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-837I-CL1-REQUIRED",
                    f"837I claim {clm.el_str(1) if clm else block.hl_subscriber_id!r} is missing the "
                    "required CL1 institutional claim code segment.",
                    segment_id="CL1",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.43",
                )
            )
    return findings


@LAYER3.register(
    "L3-837I-STATEMENT-DATES-REQUIRED",
    "837I claims must include DTP*434 statement from/through dates in loop 2300.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.42 (837I) -- DTP*434 statement dates REQ=Y.",
)
def rule_837i_statement_dates_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        dtp_434 = [d for d in block.find("DTP") if d.el_str(1) == "434"]
        if not dtp_434:
            clm = block.clm()
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-837I-STATEMENT-DATES-REQUIRED",
                    f"837I claim {clm.el_str(1) if clm else block.hl_subscriber_id!r} is missing the "
                    "required DTP*434 statement from/through dates segment.",
                    segment_id="DTP",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.42",
                )
            )
    return findings


def _subscriber_dmg(block: ClaimBlock) -> ParsedSegment | None:
    """DMG in loop 2010BA (between NM1*IL and NM1*PR)."""
    in_subscriber = False
    for seg in block.claim_segments:
        if seg.seg_id == "NM1" and seg.el_str(1) == "IL":
            in_subscriber = True
            continue
        if in_subscriber and seg.seg_id == "NM1" and seg.el_str(1) == "PR":
            break
        if in_subscriber and seg.seg_id == "DMG":
            return seg
    return None


_VALID_DMG_GENDERS = frozenset({"M", "F", "U"})


@LAYER3.register(
    "L3-SUBSCRIBER-DMG-REQUIRED",
    "Subscriber loop (2010BA) must include DMG with D8 date format and gender M, F, or U.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.16 (837P, C2) / p.40 (837I, Y) -- "
    "Loop 2010BA DMG demographics.",
)
def rule_subscriber_dmg_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    citation = "dhs_837_encounter_companion_guide.pdf p.16/p.40"
    for block in doc.claim_blocks():
        dmg = _subscriber_dmg(block)
        clm = block.clm()
        icn = clm.el_str(1) if clm else block.hl_subscriber_id
        if dmg is None:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SUBSCRIBER-DMG-REQUIRED",
                    f"Claim {icn!r} is missing the required subscriber DMG segment in loop 2010BA.",
                    segment_id="DMG",
                    source_citation=citation,
                )
            )
            continue
        if dmg.el_str(1) != "D8":
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SUBSCRIBER-DMG-REQUIRED",
                    f"Subscriber DMG01 must be 'D8', got {dmg.el_str(1)!r}.",
                    segment_id="DMG",
                    line_number=dmg.line_number,
                    source_citation=citation,
                )
            )
        gender = dmg.el_str(3)
        if gender not in _VALID_DMG_GENDERS:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-SUBSCRIBER-DMG-REQUIRED",
                    f"Subscriber DMG03 must be one of M/F/U, got {gender!r}.",
                    segment_id="DMG",
                    line_number=dmg.line_number,
                    source_citation=citation,
                )
            )
    return findings


@LAYER3.register(
    "L3-837I-ATTENDING-UMPI-REQUIRED",
    "When an attending physician loop (NM1*71) is present on 837I, it must carry REF*G2 (UMPI).",
    source_citation="dhs_837_encounter_companion_guide.pdf p.51 (837I) -- Loop 2310A attending "
    "physician REF*G2 (C2).",
)
def rule_837i_attending_umpi_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        for nm1 in _nm1_loops_missing_ref_g2(block, "71"):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-837I-ATTENDING-UMPI-REQUIRED",
                    f"Attending physician (NM1*71) for claim under subscriber HL "
                    f"{block.hl_subscriber_id} is missing a REF*G2 (UMPI) secondary identifier.",
                    segment_id="NM1",
                    line_number=nm1.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.51",
                )
            )
    return findings


@LAYER3.register(
    "L3-837I-NTE-PATIENT-ACCOUNT-REQUIRED",
    "837I claims must include NTE*UPI with patient account number (PAC= format) in loop 2300.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.44 (837I) -- "
    "'THE PATIENT ACCOUNT NUMBER IS NOW REQUIRED TO BE SENT ON ALL 837I CLAIMS' via NTE*UPI.",
)
def rule_837i_nte_patient_account_required(doc: ParsedDocument) -> list[Finding]:
    findings = []
    citation = "dhs_837_encounter_companion_guide.pdf p.44"
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        nte_upi = [
            n
            for n in _claim_header_segments(block)
            if n.seg_id == "NTE" and n.el_str(1) == "UPI" and n.el_str(2).strip()
        ]
        clm = block.clm()
        icn = clm.el_str(1) if clm else block.hl_subscriber_id
        if not nte_upi:
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-837I-NTE-PATIENT-ACCOUNT-REQUIRED",
                    f"837I claim {icn!r} is missing required NTE*UPI patient account number in loop 2300.",
                    segment_id="NTE",
                    source_citation=citation,
                )
            )
            continue
        nte02 = nte_upi[0].el_str(2).strip()
        if not nte02.upper().startswith("PAC="):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-837I-NTE-PATIENT-ACCOUNT-REQUIRED",
                    f"837I NTE*UPI value must use PAC= prefix, got {nte02!r}.",
                    segment_id="NTE",
                    line_number=nte_upi[0].line_number,
                    source_citation=citation,
                )
            )
    return findings


@LAYER3.register(
    "L3-LINE-PAID-AMOUNT-REQUIRED-837P",
    "837P claims must report the MCO-paid amount at the line level (REF*9D) on at least one service line.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.89-90, Appendix -- Paid Amount and "
    "Allowed Amount Rules: '837P -- individual paid amounts are at line level.'",
)
def rule_line_paid_amount_required_837p(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if _claim_type(block) != "837P":
            continue
        if not _refs_in_line_groups(block, "9D"):
            clm = block.clm()
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-LINE-PAID-AMOUNT-REQUIRED-837P",
                    f"837P claim {clm.el_str(1) if clm else block.hl_subscriber_id!r} has no "
                    "line-level REF*9D paid amount on any service line.",
                    segment_id="REF",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.89-90",
                )
            )
    return findings


@LAYER3.register(
    "L3-LINE-PAID-AMOUNT-REQUIRED-837I",
    "837I claims must report MCO-paid amount via REF*9D on at least one service line "
    "(loop 2400) or REF*9C in loop 2300 (inpatient claim total).",
    source_citation="dhs_837_encounter_companion_guide.pdf p.43-44 (837I REF*9C claim level) / "
    "p.59 (837I REF*9D line level); Appendix p.89-90.",
)
def rule_line_paid_amount_required_837i(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        has_line_9d = bool(_refs_in_line_groups(block, "9D"))
        has_claim_9c = any(
            s.seg_id == "REF" and s.el_str(1) == "9C" for s in _claim_header_segments(block)
        )
        if not has_line_9d and not has_claim_9c:
            clm = block.clm()
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-LINE-PAID-AMOUNT-REQUIRED-837I",
                    f"837I claim {clm.el_str(1) if clm else block.hl_subscriber_id!r} has no "
                    "REF*9D on any service line and no claim-level REF*9C in loop 2300.",
                    segment_id="REF",
                    source_citation="dhs_837_encounter_companion_guide.pdf p.43-44/p.59",
                )
            )
    return findings


@LAYER3.register(
    "L3-837I-AMOUNT-REF-PLACEMENT",
    "837I paid/allowed REF qualifiers must appear at the correct loop level: "
    "9A/9C in loop 2300 only; 9B/9D in loop 2400 only.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.43-44 (837I REF*9A/9C at claim level) / "
    "p.59 (837I REF*9B/9D at line level).",
)
def rule_837i_amount_ref_placement(doc: ParsedDocument) -> list[Finding]:
    findings: list[Finding] = []
    citation = "dhs_837_encounter_companion_guide.pdf p.43-44/p.59"
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        for ref in _claim_header_segments(block):
            if ref.seg_id == "REF" and ref.el_str(1) in ("9B", "9D"):
                findings.append(
                    Finding(
                        "error",
                        3,
                        "L3-837I-AMOUNT-REF-PLACEMENT",
                        f"REF*{ref.el_str(1)} must not appear in loop 2300 on 837I claims "
                        "(use REF*9A/9C for claim-level amounts or REF*9B/9D at the line level).",
                        segment_id="REF",
                        line_number=ref.line_number,
                        source_citation=citation,
                    )
                )
        for ref in _refs_in_line_groups(block, "9A") + _refs_in_line_groups(block, "9C"):
            findings.append(
                Finding(
                    "error",
                    3,
                    "L3-837I-AMOUNT-REF-PLACEMENT",
                    f"REF*{ref.el_str(1)} must not appear at the service-line level on 837I claims "
                    "(use REF*9B/9D in loop 2400 or REF*9A/9C in loop 2300).",
                    segment_id="REF",
                    line_number=ref.line_number,
                    source_citation=citation,
                )
            )
    return findings


@LAYER3.register(
    "L3-LINE-PAID-AMOUNT-NOT-NEGATIVE",
    "Paid/allowed amount REF segments (9A/9B/9C/9D) must not be negative.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.89-90, Appendix -- Paid Amount and Allowed "
    "Amount Rules: '0.00 is valid, but a negative number is not.'",
)
def rule_line_paid_amount_not_negative(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for ref in doc.find("REF"):
        if ref.el_str(1) in ("9B", "9C", "9D", "9A"):
            amount = _to_decimal(ref.el_str(2))
            if amount is not None and amount < 0:
                findings.append(
                    Finding(
                        "error",
                        3,
                        "L3-LINE-PAID-AMOUNT-NOT-NEGATIVE",
                        f"REF*{ref.el_str(1)} amount ({amount}) must not be negative.",
                        segment_id="REF",
                        line_number=ref.line_number,
                        source_citation="dhs_837_encounter_companion_guide.pdf p.89-90",
                    )
                )
    return findings


@LAYER3.register(
    "L3-CLM05-3-FREQUENCY-CODE-DOCUMENTED",
    "Warn (not error) when CLM05-3=7: the retrieved DHS guide's own value tables for CLM05-3 list "
    "only 1/2/3/4/5/8, not 7, even though this project's spec defines replacement encounters as "
    "CLM05-3=7. See models/encounter.py FrequencyCode docstring for the full resolution.",
    source_citation="dhs_837_encounter_companion_guide.pdf p.17 (837P) / p.41 (837I) -- CLM05-3 value "
    "tables enumerate only 1 (Original/Admit-thru-discharge), 2-5 (interim, 837I only), and 8 (Void).",
)
def rule_clm05_3_frequency_code_documented(doc: ParsedDocument) -> list[Finding]:
    # TODO: AMBIGUOUS IN SOURCE -- this is a warning, not an error, because
    # the project's own spec mandates CLM05-3=7 for replacements despite
    # the guide's silence on that value. Revisit severity if DHS publishes
    # an updated guide that explicitly addresses code 7.
    findings = []
    for clm in doc.find("CLM"):
        freq = clm.composite(5)
        freq_code = freq[2] if len(freq) >= 3 else None
        if freq_code == "7":
            findings.append(
                Finding(
                    "warning",
                    3,
                    "L3-CLM05-3-FREQUENCY-CODE-DOCUMENTED",
                    f"CLM05-3=7 (replacement) for ICN {clm.el_str(1)!r} is not enumerated in the "
                    "retrieved DHS guide's own CLM05-3 value tables (only 1/2-5/8 are listed there); "
                    "this project uses it per the task spec's explicit instruction. See "
                    "KNOWN_LIMITATIONS.md.",
                    segment_id="CLM",
                    line_number=clm.line_number,
                    source_citation="dhs_837_encounter_companion_guide.pdf p.17/p.41",
                )
            )
    return findings


# TODO: VERIFY AGAINST dhs_837_encounter_companion_guide.pdf (or an MHCP
# provider enrollment manual not in docs/reference/) -- this toolkit could
# not confirm an explicit UMPI character-length/format specification
# anywhere the guide references REF*G2. identifiers/umpi.py assumes 8
# numeric digits (matching the only DHS-assigned-id length the guide does
# state explicitly: the member ID). This stub rule intentionally returns no
# findings; it exists so the gap is visible in `list-rules` output and is
# logged in KNOWN_LIMITATIONS.md rather than silently assumed.
@LAYER3.register(
    "L3-UMPI-FORMAT-STUB",
    "STUB (no findings produced): UMPI character-length/format is not confirmed against a retrieved "
    "source document. See KNOWN_LIMITATIONS.md.",
)
def rule_umpi_format_stub(doc: ParsedDocument) -> list[Finding]:
    return []
