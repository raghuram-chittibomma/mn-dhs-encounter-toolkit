from mn_encounter_toolkit.validator.layer3_dhs_rules import (
    rule_837i_amount_ref_placement,
    rule_billing_tin_required,
    rule_billing_umpi_required,
    rule_clm05_3_frequency_code_documented,
    rule_diagnosis_principal_qualifier,
    rule_epsdt_nu_when_no_referral,
    rule_isa_receiver_fixed,
    rule_line_paid_amount_not_negative,
    rule_line_paid_amount_required_837i,
    rule_line_paid_amount_required_837p,
    rule_member_id_eight_digits,
    rule_payer_name_fixed,
    rule_referring_umpi_required,
    rule_rendering_umpi_required,
    rule_sender_id_matches_submitter,
    rule_umpi_format_stub,
    rule_void_ref_f8_only,
)
from tests.conftest import make_doc


def _claim_with_billing(billing_extra: tuple[str, ...] = (), claim_extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    # CLM03/CLM04 are intentionally empty before the CLM05 composite -- 3
    # stars (2 empty fields) between CLM02 and CLM05, matching edi/writer.py.
    return (
        "HL*1**20*1",
        *billing_extra,
        "HL*2*1*22*0",
        "CLM*ENC1*100.00***1:B:1*Y*A*Y*Y",
        "HI*ABK:F1120",
        *claim_extra,
    )


def test_rule_billing_tin_required_fails_when_missing():
    doc = make_doc(*_claim_with_billing())
    findings = rule_billing_tin_required(doc)
    assert len(findings) == 1
    assert findings[0].source_citation is not None


def test_rule_billing_tin_required_passes_when_present():
    doc = make_doc(*_claim_with_billing(billing_extra=("REF*EI*901234567",)))
    assert rule_billing_tin_required(doc) == []


def test_rule_billing_umpi_required_fails_when_missing():
    doc = make_doc(*_claim_with_billing(billing_extra=("REF*EI*901234567",)))
    findings = rule_billing_umpi_required(doc)
    assert len(findings) == 1


def test_rule_billing_umpi_required_passes_when_present():
    doc = make_doc(*_claim_with_billing(billing_extra=("REF*EI*901234567", "REF*G2*12345678")))
    assert rule_billing_umpi_required(doc) == []


def test_rule_payer_name_fixed_fails_for_wrong_payer():
    doc = make_doc(*_claim_with_billing(claim_extra=("NM1*PR*2*SOME OTHER PAYER*****PI*999999999",)))
    findings = rule_payer_name_fixed(doc)
    assert len(findings) == 1


def test_rule_payer_name_fixed_passes_for_dhs_payer():
    doc = make_doc(*_claim_with_billing(claim_extra=("NM1*PR*2*MN DEPT OF HUMAN SERVICES*****PI*411674742",)))
    assert rule_payer_name_fixed(doc) == []


def test_rule_payer_name_fixed_ignores_second_nm1_pr_occurrence_tpl():
    # First NM1*PR (2010BB, correct) followed by a second NM1*PR that is
    # the legitimate TPL third-party payer -- must NOT be flagged.
    doc = make_doc(
        *_claim_with_billing(
            claim_extra=(
                "NM1*PR*2*MN DEPT OF HUMAN SERVICES*****PI*411674742",
                "NM1*PR*2*ACME COMMERCIAL INSURANCE*****PI*123456789",
            )
        )
    )
    assert rule_payer_name_fixed(doc) == []


def test_rule_member_id_eight_digits_fails_for_short_id():
    doc = make_doc(*_claim_with_billing(claim_extra=("NM1*IL*1*Doe*Jane****MI*1234",)))
    findings = rule_member_id_eight_digits(doc)
    assert len(findings) == 1


def test_rule_member_id_eight_digits_passes_for_eight_digit_id():
    doc = make_doc(*_claim_with_billing(claim_extra=("NM1*IL*1*Doe*Jane****MI*12345678",)))
    assert rule_member_id_eight_digits(doc) == []


def test_rule_epsdt_nu_when_no_referral_fails_when_not_nu():
    doc = make_doc("CRC*ZZ*N*ST")
    findings = rule_epsdt_nu_when_no_referral(doc)
    assert len(findings) == 1


def test_rule_epsdt_nu_when_no_referral_passes_when_nu():
    doc = make_doc("CRC*ZZ*N*NU")
    assert rule_epsdt_nu_when_no_referral(doc) == []


def test_rule_epsdt_nu_when_no_referral_ignores_yes_referral():
    doc = make_doc("CRC*ZZ*Y*ST")
    assert rule_epsdt_nu_when_no_referral(doc) == []


def test_rule_void_ref_f8_only_fails_when_used_on_non_void_claim():
    doc = make_doc(*_claim_with_billing(claim_extra=("REF*F8*ORIGINALICN",)))
    findings = rule_void_ref_f8_only(doc)
    assert len(findings) == 1


def test_rule_diagnosis_principal_qualifier_fails_for_wrong_qualifier():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:B:1*Y*A*Y*Y", "HI*ABF:F1120",
    )
    findings = rule_diagnosis_principal_qualifier(doc)
    assert len(findings) == 1


def test_rule_line_paid_amount_required_837p_fails_without_ref_9d():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:B:1*Y*A*Y*Y", "HI*ABK:F1120",
        "LX*1", "SV1*HC:99213*100.00*UN*1***1",
    )
    findings = rule_line_paid_amount_required_837p(doc)
    assert len(findings) == 1


def test_rule_line_paid_amount_required_837p_passes_with_ref_9d():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:B:1*Y*A*Y*Y", "HI*ABK:F1120",
        "LX*1", "SV1*HC:99213*100.00*UN*1***1", "REF*9D*80.00",
    )
    assert rule_line_paid_amount_required_837p(doc) == []


def test_rule_line_paid_amount_required_837i_fails_without_ref_9d_or_claim_9c():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:A:1*Y*A*Y*Y", "HI*ABK:F1120",
        "LX*1", "SV2*0450*HC:99223*100.00",
    )
    findings = rule_line_paid_amount_required_837i(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L3-LINE-PAID-AMOUNT-REQUIRED-837I"


def test_rule_line_paid_amount_required_837i_passes_with_line_ref_9d():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:A:1*Y*A*Y*Y", "HI*ABK:F1120",
        "LX*1", "SV2*0450*HC:99223*100.00", "REF*9D*80.00",
    )
    assert rule_line_paid_amount_required_837i(doc) == []


def test_rule_line_paid_amount_required_837i_passes_with_claim_ref_9c():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:A:1*Y*A*Y*Y", "HI*ABK:F1120",
        "REF*9C*80.00",
        "LX*1", "SV2*0450*HC:99223*100.00",
    )
    assert rule_line_paid_amount_required_837i(doc) == []


def test_rule_837i_amount_ref_placement_fails_for_9c_on_line():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:A:1*Y*A*Y*Y", "HI*ABK:F1120",
        "LX*1", "SV2*0450*HC:99223*100.00", "REF*9C*80.00",
    )
    findings = rule_837i_amount_ref_placement(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L3-837I-AMOUNT-REF-PLACEMENT"


def test_rule_837i_amount_ref_placement_fails_for_9d_in_claim_header():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:A:1*Y*A*Y*Y", "HI*ABK:F1120",
        "REF*9D*80.00",
        "LX*1", "SV2*0450*HC:99223*100.00",
    )
    findings = rule_837i_amount_ref_placement(doc)
    assert len(findings) == 1


def test_rule_837i_amount_ref_placement_passes_for_dual_path_valid():
    doc = make_doc(
        "HL*1**20*1", "HL*2*1*22*0", "CLM*ENC1*100.00***1:A:1*Y*A*Y*Y", "HI*ABK:F1120",
        "REF*9C*80.00",
        "LX*1", "SV2*0450*HC:99223*100.00", "REF*9D*40.00",
    )
    assert rule_837i_amount_ref_placement(doc) == []


def test_rule_line_paid_amount_not_negative_fails_for_negative_value():
    doc = make_doc("REF*9D*-5.00")
    findings = rule_line_paid_amount_not_negative(doc)
    assert len(findings) == 1


def test_rule_line_paid_amount_not_negative_passes_for_zero():
    doc = make_doc("REF*9D*0.00")
    assert rule_line_paid_amount_not_negative(doc) == []


def test_rule_clm05_3_frequency_code_documented_warns_for_code_7():
    doc = make_doc("CLM*ENC1*100.00***1:B:7*Y*A*Y*Y")
    findings = rule_clm05_3_frequency_code_documented(doc)
    assert len(findings) == 1
    assert findings[0].severity == "warning"


def test_rule_clm05_3_frequency_code_documented_silent_for_code_1():
    doc = make_doc("CLM*ENC1*100.00***1:B:1*Y*A*Y*Y")
    assert rule_clm05_3_frequency_code_documented(doc) == []


def test_rule_umpi_format_stub_always_returns_no_findings():
    """Documents that this rule is a deliberate, logged stub (see
    KNOWN_LIMITATIONS.md) -- not a silently-broken check."""
    doc = make_doc("REF*G2*12345678")
    assert rule_umpi_format_stub(doc) == []


_ISA = (
    "ISA*00*          *00*          *ZZ*1234567890     *ZZ*411674742      *240101*0800*^*00501*000000001*0*T*:"
)

_ISA_DHS_RECEIVER = (
    "ISA*00*          *00*          *ZZ*1234567890     *30*41-1674742     *240101*0800*^*00501*000000001*0*T*:"
)


def test_rule_sender_id_matches_submitter_passes_when_isa_gs_align():
    doc = make_doc(_ISA, "GS*HC*1234567890*411674742*20240101*0800*1*X*005010X222A1")
    assert rule_sender_id_matches_submitter(doc) == []


def test_rule_sender_id_matches_submitter_fails_when_gs02_differs():
    doc = make_doc(_ISA, "GS*HC*WRONGSUBMIT*411674742*20240101*0800*1*X*005010X222A1")
    findings = rule_sender_id_matches_submitter(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L3-SENDER-ID-MATCHES-SUBMITTER"


def test_rule_sender_id_matches_submitter_fails_when_nm1_41_differs():
    doc = make_doc(
        _ISA,
        "GS*HC*1234567890*411674742*20240101*0800*1*X*005010X222A1",
        "NM1*41*2*MCO NAME*****46*9999999999",
    )
    findings = rule_sender_id_matches_submitter(doc)
    assert len(findings) == 1
    assert "NM109" in findings[0].message


def test_rule_isa_receiver_fixed_passes_for_dhs_envelope():
    doc = make_doc(_ISA_DHS_RECEIVER, "GS*HC*1234567890*41-1674742*20240101*0800*1*X*005010X222A1")
    assert rule_isa_receiver_fixed(doc) == []


def test_rule_isa_receiver_fixed_fails_when_isa07_not_30():
    bad_isa = (
        "ISA*00*          *00*          *ZZ*1234567890     *ZZ*41-1674742     *240101*0800*^*00501*000000001*0*T*:"
    )
    doc = make_doc(bad_isa)
    findings = rule_isa_receiver_fixed(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L3-ISA-RECEIVER-FIXED"
    assert "ISA07" in findings[0].message


def test_rule_isa_receiver_fixed_fails_when_isa08_wrong():
    bad_isa = (
        "ISA*00*          *00*          *ZZ*1234567890     *30*9999999999     *240101*0800*^*00501*000000001*0*T*:"
    )
    doc = make_doc(bad_isa)
    findings = rule_isa_receiver_fixed(doc)
    assert any(f.rule_id == "L3-ISA-RECEIVER-FIXED" and "ISA08" in f.message for f in findings)


def test_rule_isa_receiver_fixed_fails_when_gs03_differs_from_isa08():
    doc = make_doc(
        _ISA_DHS_RECEIVER,
        "GS*HC*1234567890*WRONGRECEIVER*20240101*0800*1*X*005010X222A1",
    )
    findings = rule_isa_receiver_fixed(doc)
    assert len(findings) == 1
    assert "GS03" in findings[0].message


def test_rule_referring_umpi_required_fails_when_dn_missing_ref_g2():
    doc = make_doc(*_claim_with_billing(claim_extra=("NM1*DN*1*Smith*Refer****XX*1234567890",)))
    findings = rule_referring_umpi_required(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L3-REFERRING-UMPI-REQUIRED"


def test_rule_referring_umpi_required_passes_when_ref_g2_present():
    doc = make_doc(
        *_claim_with_billing(
            claim_extra=("NM1*DN*1*Smith*Refer****XX*1234567890", "REF*G2*12345678")
        )
    )
    assert rule_referring_umpi_required(doc) == []


def test_rule_rendering_umpi_required_fails_when_82_missing_ref_g2():
    doc = make_doc(*_claim_with_billing(claim_extra=("NM1*82*1*Jones*Render****XX*9876543210",)))
    findings = rule_rendering_umpi_required(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L3-RENDERING-UMPI-REQUIRED"


def test_rule_rendering_umpi_required_passes_when_ref_g2_present():
    doc = make_doc(
        *_claim_with_billing(
            claim_extra=("NM1*82*1*Jones*Render****XX*9876543210", "REF*G2*87654321")
        )
    )
    assert rule_rendering_umpi_required(doc) == []
