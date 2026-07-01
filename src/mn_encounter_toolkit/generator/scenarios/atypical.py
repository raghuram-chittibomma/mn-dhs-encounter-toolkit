"""Atypical provider scenario: no NPI under MN statute.

SOURCE: dhs_837_encounter_companion_guide.pdf -- p.14/p.38 Loop 2010AA:
NM108/NM109 (NPI) is conditional (C1); REF*EI (TIN) is required (Y)
regardless. p.16/p.40-44 Loop 2310B/2330B etc.: REF*G2 carries the UMPI as
secondary identifier. For an atypical provider, NM108/NM109 are omitted
entirely (no NPI exists to send) and REF*EI (TIN) becomes the only primary
identifier, with REF*G2 (UMPI) still sent as secondary.
"""

from __future__ import annotations

import random
from decimal import Decimal

from mn_encounter_toolkit.generator.entities import generate_encounter_id
from mn_encounter_toolkit.generator.scenarios.common import (
    allocate_mco_paid,
    base_actors,
    build_diagnoses,
    build_mco_adjudication,
    build_professional_service_lines,
)
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.models.encounter import Encounter


@register_scenario("atypical_provider", "No NPI: TIN as primary, G2 qualifier, UMPI as secondary")
def atypical_provider(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng, billing_atypical=True, rendering_atypical=True)
    diagnoses = build_diagnoses(rng, n=2)
    lines = build_professional_service_lines(rng, diagnoses, n=2)
    total_charge = sum((l.charge_amount for l in lines), Decimal("0.00"))
    mco_paid = (total_charge * Decimal("0.80")).quantize(Decimal("0.01"))
    lines = allocate_mco_paid(lines, mco_paid)
    return Encounter(
        encounter_id=generate_encounter_id(rng),
        claim_type="837P",
        frequency_code="1",
        original_icn=None,
        mco=mco,
        billing_provider=billing,
        rendering_provider=rendering,
        member=member,
        total_charge_amount=total_charge,
        mco_paid_amount=mco_paid,
        mco_adjudication=build_mco_adjudication(paid_amount=mco_paid),
        diagnoses=diagnoses,
        service_lines=lines,
        scenario_name="atypical_provider",
    )
