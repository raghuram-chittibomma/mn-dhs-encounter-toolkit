"""EPSDT / Teen Checkup (Child and Teen Checkup, C&TC) scenario."""

from __future__ import annotations

import dataclasses
import random

from mn_encounter_toolkit.generator.scenarios.clean import clean_professional_original
from mn_encounter_toolkit.generator.scenarios.common import epsdt_info
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.models.encounter import Encounter


@register_scenario("epsdt_teen_checkup", "837P with EPSDT/Teen Checkup CRC codes")
def epsdt_teen_checkup(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    return dataclasses.replace(
        base,
        epsdt=epsdt_info(rng, referral_given=True),
        scenario_name="epsdt_teen_checkup",
    )
