"""Void and replacement encounter scenarios.

SOURCE: dhs_837_encounter_companion_guide.pdf:
  - Void: p.19 (837P) / p.43 (837I) -- REF segment, REF01=F8, REF02="MCO'S
    ORIGINAL CLAIM (ICN) NUMBER. USED WHEN CLM05-3 IS 8-VOID."
  - Replacement/correction: p.19 (837P) / p.44 (837I) -- NTE segment,
    NTE01=ADD, NTE02="C=<original ICN>", "REQUIRED ICN TRACKING NUMBER WHEN
    CLAIM IS A CORRECTED VERSION OF A DHS DENIED CLAIM OR VOIDED CLAIM."
    See models/encounter.py FrequencyCode docstring for the CLM05-3=7 vs.
    the guide's own (1/8-only) value table discrepancy this project resolves.
"""

from __future__ import annotations

import dataclasses
import random

from mn_encounter_toolkit.generator.entities import generate_icn
from mn_encounter_toolkit.generator.scenarios.clean import clean_institutional_original, clean_professional_original
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.models.encounter import Encounter


@register_scenario("void_encounter", "Void (CLM05-3=8) with original MCO ICN reference")
def void_encounter(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    return dataclasses.replace(
        base,
        frequency_code="8",
        original_icn=generate_icn(rng),
        scenario_name="void_encounter",
    )


@register_scenario("replacement_encounter", "Replacement (CLM05-3=7) with original ICN")
def replacement_encounter(rng: random.Random) -> Encounter:
    base = clean_institutional_original(rng)
    return dataclasses.replace(
        base,
        frequency_code="7",
        original_icn=generate_icn(rng),
        scenario_name="replacement_encounter",
    )
