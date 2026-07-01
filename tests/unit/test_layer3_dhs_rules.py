from mn_encounter_toolkit.validator.layer3_dhs_rules import (
    rule_billing_tin_required,
    rule_billing_umpi_required,
    rule_clm05_3_frequency_code_documented,
    rule_diagnosis_principal_qualifier,
    rule_epsdt_nu_when_no_referral,
    rule_line_paid_amount_not_negative,
    rule_line_paid_amount_required_837p,
    rule_member_id_eight_digits,
    rule_payer_name_fixed,
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
