import random

from mn_encounter_toolkit.edi.parser import parse_segments
from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.response.gen_999 import generate_999_deterministic, generate_999_simulated


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
