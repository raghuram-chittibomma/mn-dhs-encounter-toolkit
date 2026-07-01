"""Zero-pay and multi-provider scenarios."""

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


@register_scenario("zero_paid_encounter", "MCO paid $0 to provider")
def zero_paid_encounter(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng)
    diagnoses = build_diagnoses(rng, n=2)
    lines = build_professional_service_lines(rng, diagnoses, n=2)
    total_charge = sum((l.charge_amount for l in lines), Decimal("0.00"))
    zero = Decimal("0.00")
    lines = allocate_mco_paid(lines, zero)
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
        mco_paid_amount=zero,
        # SOURCE: dhs_837_encounter_companion_guide.pdf p.24 -- SBR09="HM"
        # is sent "on denied claims/lines only", which is exactly the $0
        # MCO-paid case.
        mco_adjudication=build_mco_adjudication(paid_amount=zero, denied=True),
        diagnoses=diagnoses,
        service_lines=lines,
        scenario_name="zero_paid_encounter",
    )


@register_scenario("multi_provider", "Billing provider differs from rendering provider")
def multi_provider(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng, separate_rendering_provider=True)
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
        scenario_name="multi_provider",
    )
