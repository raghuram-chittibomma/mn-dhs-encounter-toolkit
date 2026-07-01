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

from mn_encounter_toolkit.edi.parser import ClaimBlock, ParsedDocument
from mn_encounter_toolkit.models.core import DHS_PAYER_ID, DHS_PAYER_NAME
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
    source_citation="dhs_837_encounter_companion_guide.pdf p.16 (837P) / p.40 (837I) -- "
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
                    source_citation="dhs_837_encounter_companion_guide.pdf p.16/p.40",
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
        refs_9d = [r for r in block.find("REF") if r.el_str(1) == "9D"]
        if not refs_9d:
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
    "L3-LINE-PAID-AMOUNT-NOT-NEGATIVE",
    "Line-level paid/allowed amounts (REF*9D/9C paid, REF*9B/9A allowed) must not be negative.",
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
