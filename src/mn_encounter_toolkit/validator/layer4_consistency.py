"""Layer 4: cross-field consistency.

These rules re-derive the same balancing checks generator/consistency.py
applies pre-write (charge totals, diagnosis pointer ranges, TPL amount
sanity, void/replacement ICN presence), but operate on *parsed X12 text*,
so they catch inconsistencies in any 837 file -- not just ones this
toolkit generated.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from mn_encounter_toolkit.edi.parser import ClaimBlock, ParsedDocument
from mn_encounter_toolkit.validator.findings import Finding
from mn_encounter_toolkit.validator.rule_registry import RuleRegistry

LAYER4 = RuleRegistry(layer=4)


def _to_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _claim_type(block: ClaimBlock) -> str:
    sv2 = block.find("SV2")
    return "837I" if sv2 else "837P"


@LAYER4.register("L4-CHARGE-BALANCE", "CLM02 (total claim charge) must equal the sum of all service line charge amounts.")
def rule_charge_balance(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        clm02 = _to_decimal(clm.el_str(2))
        if clm02 is None:
            continue
        claim_type = _claim_type(block)
        line_total = Decimal("0.00")
        for sv in block.find("SV2" if claim_type == "837I" else "SV1"):
            charge_idx = 3 if claim_type == "837I" else 2
            charge = _to_decimal(sv.el_str(charge_idx))
            if charge is not None:
                line_total += charge
        if clm02 != line_total:
            findings.append(
                Finding(
                    "error",
                    4,
                    "L4-CHARGE-BALANCE",
                    f"CLM02 ({clm02}) does not equal the sum of service line charges ({line_total}) "
                    f"for ICN {clm.el_str(1)!r}.",
                    segment_id="CLM",
                    line_number=clm.line_number,
                )
            )
    return findings


@LAYER4.register("L4-DX-POINTER-RANGE", "Each service line's diagnosis code pointer(s) must reference an existing HI position on the same claim.")
def rule_dx_pointer_range(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        n_dx = len(block.find("HI"))
        claim_type = _claim_type(block)
        if claim_type == "837I":
            continue  # 837I SV2 does not carry a diagnosis-pointer composite in this writer's mapping
        for sv1 in block.find("SV1"):
            pointers = sv1.composite(7)
            for p in pointers:
                if not p:
                    continue
                try:
                    p_int = int(p)
                except ValueError:
                    findings.append(
                        Finding("error", 4, "L4-DX-POINTER-RANGE", f"Diagnosis pointer {p!r} is not numeric.",
                                segment_id="SV1", line_number=sv1.line_number)
                    )
                    continue
                if not (1 <= p_int <= n_dx):
                    findings.append(
                        Finding(
                            "error",
                            4,
                            "L4-DX-POINTER-RANGE",
                            f"Diagnosis pointer {p_int} does not reference an existing HI position "
                            f"(claim has {n_dx} diagnoses).",
                            segment_id="SV1",
                            line_number=sv1.line_number,
                        )
                    )
    return findings


@LAYER4.register("L4-MCO-PAID-NOT-EXCEED-CHARGE", "The MCO's reported paid amount (2320 AMT*D, first occurrence) must not exceed CLM02.")
def rule_mco_paid_not_exceed_charge(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        clm02 = _to_decimal(clm.el_str(2))
        amts = block.find("AMT")
        first_d = next((a for a in amts if a.el_str(1) == "D"), None)
        if clm02 is None or first_d is None:
            continue
        paid = _to_decimal(first_d.el_str(2))
        if paid is not None and paid > clm02:
            findings.append(
                Finding(
                    "error",
                    4,
                    "L4-MCO-PAID-NOT-EXCEED-CHARGE",
                    f"MCO-paid amount ({paid}) exceeds CLM02 total charge ({clm02}) for ICN {clm.el_str(1)!r}.",
                    segment_id="AMT",
                    line_number=first_d.line_number,
                )
            )
    return findings


@LAYER4.register(
    "L4-VOID-REPLACEMENT-HAS-ICN",
    "CLM05-3 of 7 (replacement) or 8 (void) must carry an original-ICN reference (REF*F8 or NTE*ADD 'C=').",
)
def rule_void_replacement_has_icn(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        freq = clm.composite(5)
        freq_code = freq[2] if len(freq) >= 3 else None
        if freq_code not in ("7", "8"):
            continue
        ref_f8 = [r for r in block.find("REF") if r.el_str(1) == "F8"]
        nte_add = [n for n in block.find("NTE") if n.el_str(1) == "ADD" and n.el_str(2).startswith("C=")]
        if freq_code == "8" and not ref_f8:
            findings.append(
                Finding(
                    "error",
                    4,
                    "L4-VOID-REPLACEMENT-HAS-ICN",
                    f"Void claim (CLM05-3=8, ICN {clm.el_str(1)!r}) is missing a REF*F8 original-ICN reference.",
                    segment_id="CLM",
                    line_number=clm.line_number,
                )
            )
        if freq_code == "7" and not (ref_f8 or nte_add):
            findings.append(
                Finding(
                    "error",
                    4,
                    "L4-VOID-REPLACEMENT-HAS-ICN",
                    f"Replacement claim (CLM05-3=7, ICN {clm.el_str(1)!r}) is missing an ICN tracking "
                    "reference (REF*F8 or NTE*ADD 'C=<icn>').",
                    segment_id="CLM",
                    line_number=clm.line_number,
                )
            )
    return findings


@LAYER4.register("L4-TPL-AMOUNTS-BALANCE", "If a second (TPL) 2320 occurrence is present, its reported amounts must not exceed CLM02.")
def rule_tpl_amounts_balance(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        clm02 = _to_decimal(clm.el_str(2))
        sbrs = block.find("SBR")
        if len(sbrs) < 2 or clm02 is None:
            continue
        # The second SBR onward is the TPL occurrence(s); gather the AMT
        # segments that follow the *last* SBR (our writer emits exactly one
        # AMT*D/AMT*EAF/AMT*A8 trio per SBR occurrence, in SBR order).
        amts = block.find("AMT")
        if len(amts) < 6:
            continue
        tpl_amts = amts[3:6]
        total = sum((_to_decimal(a.el_str(2)) or Decimal("0.00")) for a in tpl_amts)
        if total > clm02:
            findings.append(
                Finding(
                    "error",
                    4,
                    "L4-TPL-AMOUNTS-BALANCE",
                    f"TPL-reported amounts (paid+liability+non-covered = {total}) exceed CLM02 "
                    f"({clm02}) for ICN {clm.el_str(1)!r}.",
                    segment_id="AMT",
                    line_number=tpl_amts[0].line_number,
                )
            )
    return findings


@LAYER4.register("L4-INSTITUTIONAL-DATE-ORDER", "For 837I claims, admission date must be on or before discharge date.")
def rule_institutional_date_order(doc: ParsedDocument) -> list[Finding]:
    findings = []
    for block in doc.claim_blocks():
        if _claim_type(block) != "837I":
            continue
        admission_dtp = next((d for d in block.find("DTP") if d.el_str(1) == "435"), None)
        statement_dtp = next((d for d in block.find("DTP") if d.el_str(1) == "434"), None)
        if admission_dtp is None or statement_dtp is None:
            continue
        admission_date = admission_dtp.el_str(3)[:8]
        period = statement_dtp.el_str(3)
        if "-" not in period:
            continue
        _, through = period.split("-", 1)
        if admission_date and through and admission_date > through:
            findings.append(
                Finding(
                    "error",
                    4,
                    "L4-INSTITUTIONAL-DATE-ORDER",
                    f"Admission date ({admission_date}) is after the statement-through date ({through}).",
                    segment_id="DTP",
                    line_number=admission_dtp.line_number,
                )
            )
    return findings
