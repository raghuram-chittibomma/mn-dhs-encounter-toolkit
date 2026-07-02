from mn_encounter_toolkit.edi.parser import parse_segments
from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.edi.x12_core import Separators, detect_separators
from mn_encounter_toolkit.generator.scenarios import registry


def test_default_separators_are_detected_from_isa():
    encounter = registry.build_encounter("clean_professional_original", seed=1)
    text = write_batch_checked([encounter])
    seps = detect_separators(text)
    assert seps.element_separator == "*"
    assert seps.segment_terminator == "~"
    assert seps.sub_element_separator == ":"
    assert seps.repetition_separator == "["  # DHS-documented preference, p.35


def test_custom_separators_round_trip():
    custom = Separators(segment_terminator="\\", element_separator="^", sub_element_separator="&", repetition_separator="!")
    encounter = registry.build_encounter("clean_professional_original", seed=2)
    text = write_batch_checked([encounter], separators=custom)
    assert text.startswith("ISA^")
    detected = detect_separators(text)
    assert detected == custom
    doc = parse_segments(text, separators=detected)
    assert doc.first("ISA") is not None
    assert doc.first("CLM").el_str(1) == encounter.encounter_id


def test_parsed_document_recovers_clm_total_charge():
    encounter = registry.build_encounter("clean_professional_original", seed=3)
    text = write_batch_checked([encounter])
    doc = parse_segments(text)
    clm = doc.first("CLM")
    assert clm is not None
    assert clm.el_str(1) == encounter.encounter_id
    assert clm.el_str(2) == f"{encounter.total_charge_amount:.2f}"


def test_claim_blocks_groups_one_block_per_encounter():
    encounters = [
        registry.build_encounter("clean_professional_original", seed=4),
        registry.build_encounter("clean_institutional_original", seed=5),
    ]
    text = write_batch_checked(encounters)
    doc = parse_segments(text)
    blocks = doc.claim_blocks()
    assert len(blocks) == 2
    assert {b.clm().el_str(1) for b in blocks} == {e.encounter_id for e in encounters}


def test_claim_block_hl_hierarchy_ids_are_sequential():
    encounters = [
        registry.build_encounter("clean_professional_original", seed=6),
        registry.build_encounter("clean_professional_original", seed=7),
    ]
    text = write_batch_checked(encounters)
    doc = parse_segments(text)
    blocks = doc.claim_blocks()
    assert blocks[0].hl_billing_id == "1"
    assert blocks[0].hl_subscriber_id == "2"
    assert blocks[0].hl_subscriber_parent_id == "1"
    assert blocks[1].hl_billing_id == "3"
    assert blocks[1].hl_subscriber_id == "4"


def test_writer_emits_newline_after_every_segment_for_line_tracking():
    encounter = registry.build_encounter("clean_professional_original", seed=8)
    text = write_batch_checked([encounter])
    doc = parse_segments(text)
    # Every segment must have a distinct, monotonically non-decreasing line number.
    line_numbers = [s.line_number for s in doc.segments]
    assert line_numbers == sorted(line_numbers)
    assert len(set(line_numbers)) > 1


def test_writer_837i_line_level_uses_ref_9d_not_9c():
    encounter = registry.build_encounter("clean_institutional_original", seed=10)
    text = write_batch_checked([encounter])
    assert "REF*9D*" in text
    after_first_lx = text.split("LX*", 1)[1]
    assert "REF*9C*" not in after_first_lx


def test_writer_837i_claim_level_emits_ref_9c_when_configured():
    encounter = registry.build_encounter("clean_institutional_inpatient_claim_total", seed=11)
    text = write_batch_checked([encounter])
    before_lx, _after = text.split("LX*", 1)
    assert "REF*9C*" in before_lx
    assert "REF*9D*" not in text


def test_writer_err_missing_cl1_837i_omits_cl1_segment():
    encounter = registry.build_encounter("err_missing_cl1_837i", seed=12)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    assert "CL1*" not in text
    assert "DTP*434*" in text


def test_writer_err_missing_statement_dates_837i_omits_dtp_434():
    encounter = registry.build_encounter("err_missing_statement_dates_837i", seed=13)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    assert "DTP*434*" not in text
    assert "CL1*" in text


def test_writer_837i_emits_nte_upi_and_attending():
    encounter = registry.build_encounter("clean_institutional_original", seed=14)
    text = write_batch_checked([encounter])
    assert "NTE*UPI*PAC=" in text
    assert "NM1*71*" in text
    assert "NM1*77*" in text
    assert "REF*G2*" in text


def test_parser_rejects_trailing_unterminated_content():
    import pytest

    encounter = registry.build_encounter("clean_professional_original", seed=9)
    text = write_batch_checked([encounter])
    truncated = text.rstrip("\n") + "\nGARBAGE WITH NO TERMINATOR"
    with pytest.raises(ValueError, match="Trailing content"):
        parse_segments(truncated)
