"""Named-scenario registry.

New scenarios are added by writing a function and decorating it with
`@register_scenario("name")` in any module under generator/scenarios/ that
gets imported by generator/scenarios/__init__.py -- core generation logic
(entities.py, consistency.py, edi/writer.py) never needs to change.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from mn_encounter_toolkit.models.encounter import Encounter

ScenarioFunc = Callable[[random.Random], Encounter]


@dataclass(frozen=True)
class ScenarioInfo:
    name: str
    description: str
    func: ScenarioFunc
    is_error_scenario: bool  # True for err_* scenarios that intentionally violate a rule


_REGISTRY: dict[str, ScenarioInfo] = {}


def register_scenario(name: str, description: str) -> Callable[[ScenarioFunc], ScenarioFunc]:
    def decorator(func: ScenarioFunc) -> ScenarioFunc:
        if name in _REGISTRY:
            raise ValueError(f"Scenario {name!r} is already registered.")
        _REGISTRY[name] = ScenarioInfo(
            name=name,
            description=description,
            func=func,
            is_error_scenario=name.startswith("err_"),
        )
        return func

    return decorator


def get_scenario(name: str) -> ScenarioInfo:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"Unknown scenario {name!r}. Available: {available}") from exc


def list_scenarios() -> list[ScenarioInfo]:
    return [_REGISTRY[name] for name in sorted(_REGISTRY)]


def build_encounter(name: str, seed: int) -> Encounter:
    """Deterministic: the same (name, seed) pair always returns an
    identical Encounter, since every scenario function only consumes
    randomness from the rng instance created here."""
    rng = random.Random(seed)
    return get_scenario(name).func(rng)
