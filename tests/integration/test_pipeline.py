"""End-to-end pipeline tests: generate -> write -> parse -> validate ->
gen999 -> gen835e, using the generator's own output as fixtures (per the
spec: tests must not shell out to the CLI for fixture creation -- CLI
behavior itself is covered separately in tests/integration/test_cli.py).
"""

from __future__ import annotations

import random

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.response.gen_835e import generate_835e_deterministic
from mn_encounter_toolkit.response.gen_999 import generate_999_deterministic
from mn_encounter_toolkit.validator.findings import exit_code_for
from mn_encounter_toolkit.validator.layer1_envelope import LAYER1
from mn_encounter_toolkit.validator.run import validate_text

_CLEAN_SCENARIOS = [
    info.name for info in registry.list_scenarios() if not info.is_error_scenario
]
_ERROR_SCENARIOS = [
    info.name for info in registry.list_scenarios() if info.is_error_scenario
]

_EXPECTED_ERRORS: dict[str, str] = {
    "err_missing_umpi": "L3-BILLING-UMPI-REQUIRED",
    "err_missing_mco_paid": "L3-LINE-PAID-AMOUNT-REQUIRED-837P",
    "err_void_no_icn": "L4-VOID-REPLACEMENT-HAS-ICN",
    "err_replacement_no_icn": "L4-VOID-REPLACEMENT-HAS-ICN",
    "err_charge_mismatch": "L4-CHARGE-BALANCE",
    "err_invalid_dx_pointer": "L4-DX-POINTER-RANGE",
    "err_tpl_amounts_unbalanced": "L4-TPL-AMOUNTS-BALANCE",
    "err_bad_envelope": "L1-ISA-IEA-CONTROL-MATCH",
}


def test_every_clean_scenario_validates_with_no_errors():
    rng = random.Random(2024)
    for name in _CLEAN_SCENARIOS:
        encounter = registry.get_scenario(name).func(rng)
        text = write_batch_checked([encounter])
        findings = validate_text(text)
        errors = [f for f in findings if f.severity == "error"]
        assert errors == [], f"scenario {name!r} produced unexpected error(s): {errors}"
        assert exit_code_for(findings) == 0


def test_every_error_scenario_validates_with_expected_rule():
    rng = random.Random(2025)
    for name, expected_rule in _EXPECTED_ERRORS.items():
        encounter = registry.get_scenario(name).func(rng)
        text = write_batch_checked([encounter], allow_inconsistent=True)
        findings = validate_text(text)
        errors = [f for f in findings if f.severity == "error"]
        assert errors, f"scenario {name!r} (an err_* fixture) produced no errors at all"
        assert any(f.rule_id == expected_rule for f in errors), (
            f"scenario {name!r} should trigger {expected_rule!r}, got: "
            f"{[f.rule_id for f in errors]}"
        )
        assert exit_code_for(findings) == 1


def test_full_pipeline_clean_batch_produces_accepting_999_and_835e():
    rng = random.Random(7)
    encounters = [
        registry.get_scenario("clean_professional_original").func(rng),
        registry.get_scenario("clean_institutional_original").func(rng),
        registry.get_scenario("professional_with_tpl").func(rng),
    ]
    text = write_batch_checked(encounters)

    findings = validate_text(text)
    assert exit_code_for(findings) == 0

    ack_999 = generate_999_deterministic(text)
    assert "AK9*A" in ack_999
    assert exit_code_for(validate_text(ack_999, layers=(LAYER1,))) == 0

    remit_835e = generate_835e_deterministic(text)
    assert "CLP*" in remit_835e
    assert exit_code_for(validate_text(remit_835e, layers=(LAYER1,))) == 0
    # Every encounter's ICN must show up as a CLP01 in the remittance.
    for enc in encounters:
        assert f"CLP*{enc.encounter_id}*" in remit_835e


def test_full_pipeline_error_batch_produces_rejecting_999():
    rng = random.Random(8)
    encounters = [
        registry.get_scenario("err_bad_envelope").func(rng),
    ]
    text = write_batch_checked(encounters, allow_inconsistent=True)
    ack_999 = generate_999_deterministic(text)
    assert "AK9*R" in ack_999


def test_validating_a_999_or_835e_file_itself_does_not_crash_layer1():
    """999/835E are not 837s, but Layer 1's envelope rules are
    transaction-agnostic (ISA/GS/ST mechanics) and must not crash on them
    -- only Layers 2-4 assume 837-shaped content."""
    from mn_encounter_toolkit.edi.parser import parse_segments

    rng = random.Random(9)
    encounter = registry.get_scenario("clean_professional_original").func(rng)
    text = write_batch_checked([encounter])
    ack_999 = generate_999_deterministic(text)
    doc = parse_segments(ack_999)
    findings = LAYER1.run(doc)
    assert all(f.severity != "error" for f in findings)
