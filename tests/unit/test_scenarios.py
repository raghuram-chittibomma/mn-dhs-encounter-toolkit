import pytest

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.consistency import InconsistentEncounterError, find_inconsistencies
from mn_encounter_toolkit.generator.scenarios import registry


def test_at_least_one_scenario_of_each_kind_registered():
    names = {info.name for info in registry.list_scenarios()}
    assert "clean_professional_original" in names
    assert "clean_institutional_original" in names
    assert any(n.startswith("err_") for n in names)


def test_build_encounter_is_deterministic_for_same_seed():
    a = registry.build_encounter("clean_professional_original", seed=99)
    b = registry.build_encounter("clean_professional_original", seed=99)
    assert a.encounter_id == b.encounter_id
    assert a.total_charge_amount == b.total_charge_amount
    assert [l.charge_amount for l in a.service_lines] == [l.charge_amount for l in b.service_lines]


def test_build_encounter_differs_across_seeds():
    a = registry.build_encounter("clean_professional_original", seed=1)
    b = registry.build_encounter("clean_professional_original", seed=2)
    assert a.encounter_id != b.encounter_id


def test_get_scenario_unknown_name_raises_with_available_list():
    import pytest

    with pytest.raises(KeyError, match="Unknown scenario"):
        registry.get_scenario("not_a_real_scenario")


def test_every_non_error_scenario_passes_consistency_checks():
    for info in registry.list_scenarios():
        if info.is_error_scenario:
            continue
        encounter = registry.build_encounter(info.name, seed=7)
        issues = find_inconsistencies(encounter)
        assert issues == [], f"{info.name} unexpectedly inconsistent: {issues}"


def test_every_non_error_scenario_writes_without_raising():
    for info in registry.list_scenarios():
        if info.is_error_scenario:
            continue
        encounter = registry.build_encounter(info.name, seed=11)
        text = write_batch_checked([encounter])
        assert text.startswith("ISA")
        assert text.rstrip("\n").endswith("~")


def test_every_error_scenario_requires_allow_inconsistent_or_raises_or_writes_a_flawed_file():
    """Every err_* fixture must be writable with allow_inconsistent=True
    (that's its whole purpose), and writing it is what later gets caught
    by the validator -- see tests/integration/test_pipeline.py for the
    "validator actually flags it" half of this contract."""
    for info in registry.list_scenarios():
        if not info.is_error_scenario:
            continue
        encounter = registry.build_encounter(info.name, seed=13)
        text = write_batch_checked([encounter], allow_inconsistent=True)
        assert text.startswith("ISA")


def test_write_batch_checked_refuses_err_bad_envelope_without_allow_inconsistent():
    """err_bad_envelope passes find_inconsistencies (envelope flaw is file-level);
    the scenario_name guard must still block writing without the flag."""
    encounter = registry.build_encounter("err_bad_envelope", seed=14)
    assert find_inconsistencies(encounter) == []
    with pytest.raises(InconsistentEncounterError, match="err_\\* scenario"):
        write_batch_checked([encounter])
