"""Third Party Liability (TPL) / coordination-of-benefits scenarios.

SOURCE: dhs_837_encounter_companion_guide.pdf -- p.23, Loop 2320: "THIS LOOP
IS REQUIRED -- THE FIRST OCCURRENCE MUST CONTAIN INFORMATION FOR THE MCO AS
THE PRIMARY/SECONDARY PAYER. IF THE PRIMARY PAYER IS A THIRD PARTY, THE
SECOND OCCURRENCE OF THIS SEGMENT SHOULD CONTAIN A 'P' AND INFORMATION
RELATED TO THE RELEVANT THIRD PARTY PAYER." These scenarios populate both
the mandatory first (MCO) occurrence and a second (TPL) occurrence.
"""

from __future__ import annotations

import dataclasses
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
    q2,
)
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.models.encounter import Encounter


@register_scenario("professional_with_tpl", "837P with TPL payer present, COB loops populated")
def professional_with_tpl(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng, with_tpl=True)
    diagnoses = build_diagnoses(rng, n=2)
    lines = build_professional_service_lines(rng, diagnoses, n=2)
    total_charge = sum((l.charge_amount for l in lines), Decimal("0.00"))
    tpl_paid = q2(total_charge * Decimal("0.40"))
    mco_paid = total_charge - tpl_paid
    lines = allocate_mco_paid(lines, mco_paid)
    tpl = dataclasses.replace(member.tpl, paid_amount=tpl_paid)
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
        tpl=tpl,
        scenario_name="professional_with_tpl",
    )


@register_scenario("institutional_with_tpl", "837I with TPL payer")
def institutional_with_tpl(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng, with_tpl=True)
    diagnoses = build_diagnoses(rng, n=3, institutional=True)
    lines = build_institutional_service_lines(rng, diagnoses, n=3)
    total_charge = sum((l.charge_amount for l in lines), Decimal("0.00"))
    tpl_paid = q2(total_charge * Decimal("0.35"))
    mco_paid = total_charge - tpl_paid
    lines = allocate_mco_paid(lines, mco_paid)
    tpl = dataclasses.replace(member.tpl, paid_amount=tpl_paid)
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
        tpl=tpl,
        scenario_name="institutional_with_tpl",
    )
