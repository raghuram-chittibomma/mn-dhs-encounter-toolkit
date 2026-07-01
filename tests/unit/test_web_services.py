"""Web UI tests for response and scenario generation services."""

import random

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.web.generate_service import generate_batch_from_scenarios
from mn_encounter_toolkit.web.response_service import generate_835e_from_text, generate_999_from_text


def test_generate_999_deterministic_from_clean_837():
    encounter = registry.build_encounter("clean_professional_original", seed=1)
    source = write_batch_checked([encounter])
    result = generate_999_from_text(source, mode="deterministic")
    assert result.error_message is None
    assert "AK9*A" in result.output_text
    assert result.layer1_clean


def test_generate_835e_deterministic_from_clean_837():
    encounter = registry.build_encounter("clean_professional_original", seed=2)
    source = write_batch_checked([encounter])
    result = generate_835e_from_text(source, mode="deterministic")
    assert result.error_message is None
    assert "CLP*" in result.output_text
    assert result.layer1_clean


def test_scenario_lab_generates_clean_batch():
    result = generate_batch_from_scenarios(
        ["clean_professional_original"],
        seed=42,
    )
    assert result.error_message is None
    assert result.encounter_count == 1
    assert result.output_text.startswith("ISA")


def test_scenario_lab_refuses_mixed_err_without_flag():
    result = generate_batch_from_scenarios(
        ["clean_professional_original", "err_missing_umpi"],
        seed=99,
    )
    assert result.error_message is not None


def test_generate_999_simulation_is_deterministic_for_seed():
    encounter = registry.build_encounter("clean_professional_original", seed=3)
    source = write_batch_checked([encounter])
    a = generate_999_from_text(source, mode="simulation", seed=77, outcome_weights="A=1,E=0,R=0")
    b = generate_999_from_text(source, mode="simulation", seed=77, outcome_weights="A=1,E=0,R=0")
    assert a.output_text == b.output_text
