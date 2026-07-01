"""Importing this package registers every named scenario.

Add a new scenario by creating (or extending) a module here with a
`@register_scenario(...)`-decorated function and importing that module
below -- no other code in the toolkit needs to change.
"""

from mn_encounter_toolkit.generator.scenarios import (  # noqa: F401
    atypical,
    clean,
    epsdt,
    errors,
    misc,
    programs,
    tpl,
    void_replacement,
)
from mn_encounter_toolkit.generator.scenarios.registry import (
    ScenarioInfo,
    build_encounter,
    get_scenario,
    list_scenarios,
    register_scenario,
)

__all__ = [
    "ScenarioInfo",
    "build_encounter",
    "get_scenario",
    "list_scenarios",
    "register_scenario",
]
