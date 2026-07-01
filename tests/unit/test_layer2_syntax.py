from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.validator.layer2_syntax import (
    rule_amt02_money_format,
    rule_clm02_money_format,
    rule_diagnosis_code_no_decimal,
    rule_dtp_date8_format,
    rule_hl_level_code_known,
    rule_nm1_entity_type_qualifier,
    rule_npi_check_digit_valid,
    rule_st01_value,
)
from tests.conftest import make_doc

_MINIMAL = (
    "ISA*00*          *00*          *ZZ*1234567890     *ZZ*411674742      *240101*0800*[*00501*000000001*0*T*:",
    "GS*HC*1234567890*411674742*20240101*0800*1*X*005010X222A1",
    "ST*837*1*005010X222A1",
    "SE*2*1",
    "GE*1*1",
    "IEA*1*000000001",
)


def test_rule_st01_value_passes_for_837():
    doc = make_doc(*_MINIMAL)
    assert rule_st01_value(doc) == []


def test_rule_st01_value_fails_for_wrong_transaction_set():
    segs = list(_MINIMAL)
    segs[2] = "ST*835*1*005010X221A1"
    doc = make_doc(*segs)
    findings = rule_st01_value(doc)
    assert len(findings) == 1
    assert "got '835'" in findings[0].message


def test_rule_clm02_money_format_rejects_negative_and_missing_cents():
    doc = make_doc("CLM*ENC1*-5.00***1:B:1*Y*A*Y*Y")
    findings = rule_clm02_money_format(doc)
    assert len(findings) == 1
    doc2 = make_doc("CLM*ENC1*100*1:B:1*Y*A*Y*Y")
    findings2 = rule_clm02_money_format(doc2)
    assert len(findings2) == 1


def test_rule_clm02_money_format_passes_for_valid_amount():
    doc = make_doc("CLM*ENC1*100.00**1:B:1*Y*A*Y*Y")
    assert rule_clm02_money_format(doc) == []


def test_rule_amt02_money_format_rejects_bad_value():
    doc = make_doc("AMT*D*not-a-number")
    findings = rule_amt02_money_format(doc)
    assert len(findings) == 1
    assert "D" in findings[0].message


def test_rule_dtp_date8_format_rejects_invalid_calendar_date():
    doc = make_doc("DTP*472*D8*20240230")  # Feb 30 doesn't exist
    findings = rule_dtp_date8_format(doc)
    assert len(findings) == 1


def test_rule_dtp_date8_format_ignores_non_d8_qualifier():
    doc = make_doc("DTP*434*RD8*20240101-20240105")
    assert rule_dtp_date8_format(doc) == []


def test_rule_nm1_entity_type_qualifier_rejects_bad_value():
    doc = make_doc("NM1*85*9*Smith*John")
    findings = rule_nm1_entity_type_qualifier(doc)
    assert len(findings) == 1


def test_rule_hl_level_code_known_rejects_unrecognized_level():
    doc = make_doc("HL*1**99*1")
    findings = rule_hl_level_code_known(doc)
    assert len(findings) == 1


def test_rule_npi_check_digit_valid_rejects_bad_npi():
    doc = make_doc("NM1*85*2*Clinic*****XX*1234567890")  # not Luhn-valid
    findings = rule_npi_check_digit_valid(doc)
    assert len(findings) == 1


def test_rule_npi_check_digit_valid_accepts_generated_npi():
    from mn_encounter_toolkit.edi.parser import parse_segments

    encounter = registry.build_encounter("clean_professional_original", seed=1)
    text = write_batch_checked([encounter])
    doc = parse_segments(text)
    assert rule_npi_check_digit_valid(doc) == []


def test_rule_diagnosis_code_no_decimal_rejects_decimal_point():
    doc = make_doc("HI*ABK:F11.20")
    findings = rule_diagnosis_code_no_decimal(doc)
    assert len(findings) == 1


def test_rule_diagnosis_code_no_decimal_accepts_clean_code():
    doc = make_doc("HI*ABK:F1120")
    assert rule_diagnosis_code_no_decimal(doc) == []
