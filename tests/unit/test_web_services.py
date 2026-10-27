"""Web UI tests for response and scenario generation services."""

import json
from pathlib import Path

import random

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.web.edi_html import render_edi_html
from mn_encounter_toolkit.web.generate_service import generate_batch_from_scenarios
from mn_encounter_toolkit.web.response_service import generate_835e_from_text, generate_999_from_text
from mn_encounter_toolkit.web.validate_service import (
    detect_transactions,
    layers_for_upload,
    report_to_json,
    validate_upload,
)


def test_report_to_json_includes_empty_findings_for_clean_upload():
    encounter = registry.build_encounter("clean_professional_original", seed=42)
    source = write_batch_checked([encounter])
    report = validate_upload(source, filename="clean.x12")
    payload = json.loads(report_to_json(report))
    assert report.error_count == 0
    assert payload["finding_count"] == 0
    assert payload["error_count"] == 0
    assert payload["claims"]
    assert payload["enriched_findings"] == []


def test_transaction_detection_selects_layers():
    encounter = registry.build_encounter("clean_professional_original", seed=1)
    source = write_batch_checked([encounter])
    professional = detect_transactions(source)
    assert professional.kinds == ("837P",)
    assert layers_for_upload(professional, (1, 2, 3, 4)) == (1, 2, 3, 4)
    assert layers_for_upload(professional, (1, 3)) == (1, 3)

    mixed = (Path(__file__).resolve().parents[2] / "examples" / "clean_batch.x12").read_text(encoding="utf-8")
    assert detect_transactions(mixed).kinds == ("837P", "837I")

    remit = generate_835e_from_text(source, mode="deterministic").output_text
    ack = generate_999_from_text(source, mode="deterministic").output_text
    assert detect_transactions(remit).kinds == ("835",)
    assert detect_transactions(ack).kinds == ("999",)
    assert layers_for_upload(detect_transactions(remit), (1, 2, 3, 4)) == (1,)
    assert layers_for_upload(detect_transactions(ack), (1, 2, 4)) == (1,)
    assert layers_for_upload(detect_transactions("not edi"), (1, 2, 3, 4)) is None


def test_view_edi_bridge_renders_clean_batch():
    source = Path(__file__).resolve().parents[2] / "examples" / "clean_batch.x12"
    page = render_edi_html(source.read_text(encoding="utf-8"), filename=source.name)
    assert "Loop 2300" in page
    assert "Billing provider" in page


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
