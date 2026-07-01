"""Synthetic 837 generation for the scenario lab UI."""

from __future__ import annotations

import random
from dataclasses import dataclass

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.consistency import InconsistentEncounterError
from mn_encounter_toolkit.generator.scenarios import registry


@dataclass(frozen=True)
class GenerateBatchResult:
    output_text: str
    scenario_names: tuple[str, ...]
    encounter_count: int
    error_message: str | None = None


def list_scenario_options() -> list[tuple[str, str, bool]]:
    """Return (name, description, is_error_scenario) for every registered scenario."""
    return [
        (info.name, info.description, info.is_error_scenario)
        for info in registry.list_scenarios()
    ]


def generate_batch_from_scenarios(
    scenario_names: list[str],
    *,
    seed: int,
    count_per_scenario: int = 1,
) -> GenerateBatchResult:
    if not scenario_names:
        return GenerateBatchResult(
            output_text="",
            scenario_names=(),
            encounter_count=0,
            error_message="Select at least one scenario.",
        )
    rng = random.Random(seed)
    expanded: list[str] = []
    for name in scenario_names:
        expanded.extend([name] * count_per_scenario)

    try:
        encounters = [registry.get_scenario(name).func(rng) for name in expanded]
        allow = all(name.startswith("err_") for name in expanded)
        text = write_batch_checked(encounters, allow_inconsistent=allow)
    except (KeyError, InconsistentEncounterError, ValueError) as exc:
        return GenerateBatchResult(
            output_text="",
            scenario_names=tuple(expanded),
            encounter_count=0,
            error_message=str(exc),
        )

    return GenerateBatchResult(
        output_text=text,
        scenario_names=tuple(expanded),
        encounter_count=len(encounters),
    )
