"""Baseline clean (fully valid) scenarios."""

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
)
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.models.encounter import Encounter


@register_scenario(
    "clean_professional_original",
    "Valid 837P original encounter, standard provider, MCO-paid amount present, no TPL",
)
def clean_professional_original(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng)
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
        scenario_name="clean_professional_original",
    )


@register_scenario(
    "clean_institutional_original",
    "Valid 837I original, inpatient, admission/discharge dates, DRG, MCO-paid amount",
)
def clean_institutional_original(rng: random.Random) -> Encounter:
    mco, billing, rendering, member = base_actors(rng)
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
        scenario_name="clean_institutional_original",
    )


@register_scenario(
    "clean_institutional_inpatient_claim_total",
    "Valid 837I with MCO-paid amount at claim level (REF*9C/9A in loop 2300) only",
)
def clean_institutional_inpatient_claim_total(rng: random.Random) -> Encounter:
    base = clean_institutional_original(rng)
    mco_paid = base.mco_adjudication.paid_amount
    stripped_lines = tuple(
        dataclasses.replace(line, mco_paid_amount_line=None, allowed_amount_line=None)
        for line in base.service_lines
    )
    inst = dataclasses.replace(
        base.institutional,
        mco_paid_amount_claim=mco_paid,
        allowed_amount_claim=base.total_charge_amount,
    )
    return dataclasses.replace(
        base,
        service_lines=stripped_lines,
        institutional=inst,
        scenario_name="clean_institutional_inpatient_claim_total",
    )
