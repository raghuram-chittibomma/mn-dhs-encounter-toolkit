"""Program-specific scenarios (PMAP, MinnesotaCare, MSHO)."""

from __future__ import annotations

import random
from decimal import Decimal

from mn_encounter_toolkit.generator.entities import generate_encounter_id
from mn_encounter_toolkit.generator.scenarios.common import (
    allocate_mco_paid,
    base_actors,
    build_diagnoses,
    build_institutional_service_lines,
    build_mco_adjudication,
    build_professional_service_lines,
    institutional_detail,
)
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.models.encounter import Encounter


def _professional_for_program(rng: random.Random, program: str, scenario_name: str) -> Encounter:
    mco, billing, rendering, member = base_actors(rng, program=program)
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
        scenario_name=scenario_name,
    )


@register_scenario("pmap_professional", "PMAP-enrolled member, professional encounter")
def pmap_professional(rng: random.Random) -> Encounter:
    return _professional_for_program(rng, "PMAP", "pmap_professional")


@register_scenario("minnesotacare_professional", "MinnesotaCare-enrolled member")
def minnesotacare_professional(rng: random.Random) -> Encounter:
    return _professional_for_program(rng, "MinnesotaCare", "minnesotacare_professional")


@register_scenario("msho_institutional", "MSHO-enrolled member, inpatient")
def msho_institutional(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng, program="MSHO")
    diagnoses = build_diagnoses(rng, n=3, institutional=True)
    lines = build_institutional_service_lines(rng, diagnoses, n=3)
    total_charge = sum((l.charge_amount for l in lines), Decimal("0.00"))
    mco_paid = (total_charge * Decimal("0.75")).quantize(Decimal("0.01"))
    lines = allocate_mco_paid(lines, mco_paid)
    return Encounter(
        encounter_id=generate_encounter_id(rng),
        claim_type="837I",
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
        institutional=institutional_detail(rng),
        scenario_name="msho_institutional",
    )
