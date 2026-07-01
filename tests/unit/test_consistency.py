import dataclasses
from decimal import Decimal

import pytest

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.consistency import (
    InconsistentEncounterError,
    ensure_consistent,
    find_inconsistencies,
)
from tests.conftest import encounter_for


def test_clean_scenario_has_no_inconsistencies():
    encounter = encounter_for("clean_professional_original", seed=1)
    assert find_inconsistencies(encounter) == []
    ensure_consistent(encounter)  # must not raise


def test_charge_mismatch_is_detected():
    encounter = encounter_for("clean_professional_original", seed=2)
    bad = dataclasses.replace(encounter, total_charge_amount=encounter.total_charge_amount + Decimal("1.00"))
    issues = find_inconsistencies(bad)
    assert any("does not equal the sum of" in i for i in issues)


def test_mco_paid_exceeding_charge_is_detected():
    encounter = encounter_for("clean_professional_original", seed=3)
    bad = dataclasses.replace(encounter, mco_paid_amount=encounter.total_charge_amount + Decimal("50.00"))
    issues = find_inconsistencies(bad)
    assert any("exceeds total charge amount" in i for i in issues)


def test_invalid_diagnosis_pointer_is_detected():
    encounter = encounter_for("clean_professional_original", seed=4)
    bad_line = dataclasses.replace(encounter.service_lines[0], diagnosis_pointers=(99,))
    bad = dataclasses.replace(encounter, service_lines=(bad_line,) + tuple(encounter.service_lines[1:]))
    issues = find_inconsistencies(bad)
    assert any("does not reference an existing HI position" in i for i in issues)


def test_void_without_original_icn_is_detected():
    encounter = encounter_for("void_encounter", seed=5)
    bad = dataclasses.replace(encounter, original_icn=None)
    issues = find_inconsistencies(bad)
    assert any("requires original_icn" in i for i in issues)


def test_ensure_consistent_raises_with_descriptive_message():
    encounter = encounter_for("clean_professional_original", seed=6)
    bad = dataclasses.replace(encounter, total_charge_amount=encounter.total_charge_amount + Decimal("1.00"))
    with pytest.raises(InconsistentEncounterError, match="internally inconsistent"):
        ensure_consistent(bad)


def test_write_batch_checked_refuses_err_scenario_without_allow_inconsistent():
    encounter = encounter_for("err_missing_mco_paid", seed=1)
    with pytest.raises(InconsistentEncounterError, match="err_\\* scenario"):
        write_batch_checked([encounter])
