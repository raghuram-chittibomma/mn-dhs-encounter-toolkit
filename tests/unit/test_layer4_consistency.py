"""Layer 4 rules operate on doc.claim_blocks(), so each hand-built fixture
needs the minimal HL*20/HL*22 hierarchy the parser expects -- still far
smaller than a full generated encounter, demonstrating these rules are
independently testable without the generator."""

from mn_encounter_toolkit.validator.layer4_consistency import (
    rule_charge_balance,
    rule_dx_pointer_range,
    rule_institutional_date_order,
    rule_mco_paid_not_exceed_charge,
    rule_tpl_amounts_balance,
    rule_void_replacement_has_icn,
)
from tests.conftest import make_doc


def _professional_claim(clm02: str, sv1_charges: list[str], pointers: str = "1") -> tuple[str, ...]:
    # CLM03/CLM04 are intentionally empty before the CLM05 composite -- 3
    # stars (2 empty fields) between CLM02 and CLM05, matching edi/writer.py.
    segs = [
        "HL*1**20*1",
        "HL*2*1*22*0",
        f"CLM*ENC1*{clm02}***{1}:B:1*Y*A*Y*Y",
        "HI*ABK:F1120",
    ]
    for i, charge in enumerate(sv1_charges, start=1):
        segs.append("LX*" + str(i))
        segs.append(f"SV1*HC:99213*{charge}*UN*1***{pointers}")
    return tuple(segs)


def test_rule_charge_balance_passes_when_lines_sum_to_clm02():
    doc = make_doc(*_professional_claim("100.00", ["60.00", "40.00"]))
    assert rule_charge_balance(doc) == []


def test_rule_charge_balance_fails_when_lines_dont_sum_to_clm02():
    doc = make_doc(*_professional_claim("100.00", ["60.00", "30.00"]))
    findings = rule_charge_balance(doc)
    assert len(findings) == 1
    assert "ENC1" in findings[0].message


def test_rule_dx_pointer_range_fails_for_out_of_range_pointer():
    doc = make_doc(*_professional_claim("60.00", ["60.00"], pointers="5"))
    findings = rule_dx_pointer_range(doc)
    assert len(findings) == 1
    assert "claim has 1 diagnoses" in findings[0].message


def test_rule_dx_pointer_range_passes_for_valid_pointer():
    doc = make_doc(*_professional_claim("60.00", ["60.00"], pointers="1"))
    assert rule_dx_pointer_range(doc) == []


def test_rule_mco_paid_not_exceed_charge_fails_when_paid_too_high():
    segs = list(_professional_claim("100.00", ["100.00"]))
    segs.append("AMT*D*150.00")
    doc = make_doc(*segs)
    findings = rule_mco_paid_not_exceed_charge(doc)
    assert len(findings) == 1


def test_rule_mco_paid_not_exceed_charge_passes_when_paid_within_charge():
    segs = list(_professional_claim("100.00", ["100.00"]))
    segs.append("AMT*D*80.00")
    doc = make_doc(*segs)
    assert rule_mco_paid_not_exceed_charge(doc) == []


def test_rule_void_replacement_has_icn_fails_when_ref_f8_missing():
    segs = [
        "HL*1**20*1",
        "HL*2*1*22*0",
        "CLM*ENC1*100.00***1:B:8*Y*A*Y*Y",  # CLM05-3=8, void
        "HI*ABK:F1120",
    ]
    doc = make_doc(*segs)
    findings = rule_void_replacement_has_icn(doc)
    assert len(findings) == 1
    assert "Void claim" in findings[0].message


def test_rule_void_replacement_has_icn_passes_when_ref_f8_present():
    segs = [
        "HL*1**20*1",
        "HL*2*1*22*0",
        "CLM*ENC1*100.00***1:B:8*Y*A*Y*Y",
        "REF*F8*ORIGINALICN1",
        "HI*ABK:F1120",
    ]
    doc = make_doc(*segs)
    assert rule_void_replacement_has_icn(doc) == []


def test_rule_void_replacement_has_icn_passes_for_replacement_with_nte():
    segs = [
        "HL*1**20*1",
        "HL*2*1*22*0",
        "CLM*ENC1*100.00***1:B:7*Y*A*Y*Y",
        "NTE*ADD*C=ORIGINALICN1",
        "HI*ABK:F1120",
    ]
    doc = make_doc(*segs)
    assert rule_void_replacement_has_icn(doc) == []


def test_rule_tpl_amounts_balance_fails_when_tpl_exceeds_clm02():
    segs = [
        "HL*1**20*1",
        "HL*2*1*22*0",
        "CLM*ENC1*100.00***1:B:1*Y*A*Y*Y",
        "HI*ABK:F1120",
        "SBR*U*18*****MC",
        "AMT*D*80.00",
        "AMT*EAF*0.00",
        "AMT*A8*0.00",
        "SBR*P*18*****CI",
        "AMT*D*60.00",
        "AMT*EAF*50.00",
        "AMT*A8*0.00",
    ]
    doc = make_doc(*segs)
    findings = rule_tpl_amounts_balance(doc)
    assert len(findings) == 1


def test_rule_institutional_date_order_fails_when_admission_after_statement_through():
    segs = [
        "HL*1**20*1",
        "HL*2*1*22*0",
        "CLM*ENC1*100.00***11:A:1*N*A*Y*Y",
        "DTP*434*RD8*20240101-20240105",
        "DTP*435*DT*202401100800",
        "HI*ABK:F1120",
        "LX*1",
        "SV2*0250**100.00*UN*1",
    ]
    doc = make_doc(*segs)
    findings = rule_institutional_date_order(doc)
    assert len(findings) == 1
