"""Layer 1 rules are pure envelope mechanics, so each is tested directly
against a small, hand-built ParsedDocument -- no generator/writer needed."""

from mn_encounter_toolkit.validator.layer1_envelope import (
    rule_ge_st_count,
    rule_gs_ge_control_match,
    rule_iea_group_count,
    rule_iea_present,
    rule_isa13_format,
    rule_isa_iea_control_match,
    rule_isa_present,
    rule_one_isa_per_file,
    rule_se_segment_count,
    rule_separators_distinct,
    rule_st_se_control_match,
)
from tests.conftest import make_doc

_MINIMAL_OK = (
    "ISA*00*          *00*          *ZZ*1234567890     *ZZ*411674742      *240101*0800*[*00501*000000001*0*T*:",
    "GS*HC*1234567890*411674742*20240101*0800*1*X*005010X222A1",
    "ST*837*1*005010X222A1",
    "SE*2*1",
    "GE*1*1",
    "IEA*1*000000001",
)


def test_rule_isa_present_passes_when_isa_exists():
    doc = make_doc(*_MINIMAL_OK)
    assert rule_isa_present(doc) == []


def test_rule_isa_present_fails_when_isa_missing():
    doc = make_doc(*_MINIMAL_OK[1:])
    findings = rule_isa_present(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L1-ISA-PRESENT"
    assert findings[0].severity == "error"


def test_rule_iea_present_fails_when_iea_missing():
    doc = make_doc(*_MINIMAL_OK[:-1])
    findings = rule_iea_present(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L1-IEA-PRESENT"


def test_rule_one_isa_per_file_flags_second_isa():
    doc = make_doc(*_MINIMAL_OK, *_MINIMAL_OK)
    findings = rule_one_isa_per_file(doc)
    assert len(findings) == 1
    assert "2 ISA" in findings[0].message


def test_rule_isa_iea_control_match_passes_when_equal():
    doc = make_doc(*_MINIMAL_OK)
    assert rule_isa_iea_control_match(doc) == []


def test_rule_isa_iea_control_match_fails_when_different():
    segs = list(_MINIMAL_OK)
    segs[-1] = "IEA*1*000000999"
    doc = make_doc(*segs)
    findings = rule_isa_iea_control_match(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "L1-ISA-IEA-CONTROL-MATCH"


def test_rule_isa13_format_rejects_all_zero_control_number():
    segs = list(_MINIMAL_OK)
    segs[0] = segs[0].replace("000000001", "000000000")
    segs[-1] = "IEA*1*000000000"
    doc = make_doc(*segs)
    findings = rule_isa13_format(doc)
    assert any("must not be all zeros" in f.message for f in findings)


def test_rule_isa13_format_rejects_non_9_digit():
    segs = list(_MINIMAL_OK)
    segs[0] = segs[0].replace("000000001", "123")
    doc = make_doc(*segs)
    findings = rule_isa13_format(doc)
    assert any("must be exactly 9 digits" in f.message for f in findings)


def test_rule_iea_group_count_detects_mismatch():
    segs = list(_MINIMAL_OK)
    segs[-1] = "IEA*2*000000001"
    doc = make_doc(*segs)
    findings = rule_iea_group_count(doc)
    assert len(findings) == 1
    assert "declares 2" in findings[0].message


def test_rule_gs_ge_control_match_detects_mismatch():
    segs = list(_MINIMAL_OK)
    segs[-2] = "GE*1*999"
    doc = make_doc(*segs)
    findings = rule_gs_ge_control_match(doc)
    assert len(findings) == 1


def test_rule_ge_st_count_detects_mismatch():
    segs = list(_MINIMAL_OK)
    segs[-2] = "GE*5*1"
    doc = make_doc(*segs)
    findings = rule_ge_st_count(doc)
    assert len(findings) == 1
    assert "declares 5" in findings[0].message


def test_rule_st_se_control_match_detects_mismatch():
    segs = list(_MINIMAL_OK)
    segs[3] = "SE*2*999"
    doc = make_doc(*segs)
    findings = rule_st_se_control_match(doc)
    assert len(findings) == 1


def test_rule_se_segment_count_detects_mismatch():
    segs = list(_MINIMAL_OK)
    segs[3] = "SE*99*1"
    doc = make_doc(*segs)
    findings = rule_se_segment_count(doc)
    assert len(findings) == 1
    assert "declares 99" in findings[0].message


def test_rule_separators_distinct_passes_for_default_doc():
    doc = make_doc(*_MINIMAL_OK)
    assert rule_separators_distinct(doc) == []
