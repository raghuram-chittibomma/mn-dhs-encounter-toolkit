import random
from datetime import date

from mn_encounter_toolkit.validator.findings import Finding

from mn_encounter_toolkit.edi.parser import parse_segments
from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.response.gen_999 import (
    ak304_for_finding,
    build_deterministic_acks,
    generate_999_deterministic,
    generate_999_simulated,
)


def test_deterministic_999_accepts_a_clean_file():
    encounter = registry.build_encounter("clean_professional_original", seed=1)
    text = write_batch_checked([encounter])
    out = generate_999_deterministic(text)
    doc = parse_segments(out)
    assert doc.first("ST").el_str(1) == "999"
    ak5 = doc.first("AK5")
    assert ak5.el_str(1) == "A"
    ak9 = doc.first("AK9")
    assert ak9.el_str(1) == "A"


def test_deterministic_999_rejects_envelope_corruption():
    encounter = registry.build_encounter("err_bad_envelope", seed=2)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    out = generate_999_deterministic(text)
    doc = parse_segments(out)
    assert doc.first("AK9").el_str(1) == "R"
    assert doc.first("AK5").el_str(1) == "R"


def test_deterministic_999_ak1_references_original_gs():
    encounter = registry.build_encounter("clean_professional_original", seed=3)
    text = write_batch_checked([encounter])
    original = parse_segments(text)
    out = generate_999_deterministic(text)
    doc = parse_segments(out)
    ak1 = doc.first("AK1")
    original_gs = original.first("GS")
    assert ak1.el_str(1) == original_gs.el_str(1)
    assert ak1.el_str(2) == original_gs.el_str(6)


def test_deterministic_999_is_byte_identical_with_fixed_submission_time():
    encounter = registry.build_encounter("clean_professional_original", seed=12)
    text = write_batch_checked([encounter])
    kwargs = dict(submission_date=date(2026, 6, 30), submission_time="1530")
    out1 = generate_999_deterministic(text, **kwargs)
    out2 = generate_999_deterministic(text, **kwargs)
    assert out1 == out2


def test_simulated_999_is_deterministic_for_same_seed():
    encounter = registry.build_encounter("clean_professional_original", seed=4)
    text = write_batch_checked([encounter])
    out1 = generate_999_simulated(text, random.Random(77))
    out2 = generate_999_simulated(text, random.Random(77))
    assert out1 == out2


def test_simulated_999_respects_outcome_weights_all_accept():
    encounter = registry.build_encounter("clean_professional_original", seed=5)
    text = write_batch_checked([encounter])
    out = generate_999_simulated(text, random.Random(1), outcome_weights={"A": 1, "E": 0, "R": 0})
    doc = parse_segments(out)
    assert doc.first("AK5").el_str(1) == "A"


def test_simulated_999_respects_outcome_weights_all_reject():
    encounter = registry.build_encounter("clean_professional_original", seed=6)
    text = write_batch_checked([encounter])
    out = generate_999_simulated(text, random.Random(1), outcome_weights={"A": 0, "E": 0, "R": 1})
    doc = parse_segments(out)
    assert doc.first("AK5").el_str(1) == "R"
    assert len(doc.find("AK3")) >= 1


def test_deterministic_999_handles_multiple_transaction_sets_in_one_group():
    encounters = [
        registry.build_encounter("clean_professional_original", seed=7),
        registry.build_encounter("clean_professional_original", seed=8),
    ]
    text = write_batch_checked(encounters)
    out = generate_999_deterministic(text)
    doc = parse_segments(out)
    # Both encounters share one claim_type, so write_batch_checked groups
    # them into a single ST/SE transaction set -- exactly one AK2 entry.
    assert len(doc.find("AK2")) == 1


def test_ak304_for_finding_maps_rule_ids_to_segment_syntax_codes():
    assert ak304_for_finding(Finding("error", 2, "L2-BHT-PRESENT", "missing")) == "3"
    assert ak304_for_finding(Finding("error", 2, "L2-CLAIM-HAS-DIAGNOSIS", "missing")) == "I6"
    assert (
        ak304_for_finding(
            Finding("error", 2, "L2-CLM-EXACTLY-ONE-PER-CLAIM", "has 2 CLM segments (expected 1).")
        )
        == "5"
    )
    assert (
        ak304_for_finding(
            Finding("error", 2, "L2-CLM-EXACTLY-ONE-PER-CLAIM", "has 0 CLM segments (expected 1).")
        )
        == "I6"
    )
    assert (
        ak304_for_finding(Finding("error", 1, "L1-ISA-IEA-CONTROL-MATCH", "mismatch", segment_id="IEA"))
        == "8"
    )


def test_deterministic_999_uses_ak304_3_for_missing_bht():
    encounter = registry.build_encounter("clean_professional_original", seed=9)
    text = write_batch_checked([encounter])
    text_no_bht = "\n".join(line for line in text.splitlines() if not line.startswith("BHT*")) + "\n"
    _, acks = build_deterministic_acks(text_no_bht)
    segment_errors = next(iter(acks.values()))[0].segment_errors
    assert ("BHT", "3") in segment_errors


def test_deterministic_999_uses_ak304_5_for_duplicate_clm():
    encounter = registry.build_encounter("clean_professional_original", seed=10)
    text = write_batch_checked([encounter])
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("CLM*"):
            lines.insert(i + 1, line)
            break
    else:
        raise AssertionError("expected a CLM segment in generated batch")
    _, acks = build_deterministic_acks("\n".join(lines) + "\n")
    segment_errors = next(iter(acks.values()))[0].segment_errors
    assert ("CLM", "5") in segment_errors


def test_deterministic_999_uses_ak304_8_for_envelope_control_mismatch():
    encounter = registry.build_encounter("err_bad_envelope", seed=11)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    out = generate_999_deterministic(text)
    doc = parse_segments(out)
    ak3 = doc.first("AK3")
    assert ak3.el_str(4) == "8"
    assert ak3.el_str(1) == "IEA"
