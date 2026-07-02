"""Shared builder helpers used by every scenario module.

Centralizing "build a plausible, balanced claim" logic here is what lets
individual scenario functions (clean.py, tpl.py, errors.py, ...) stay short
and focused on the one thing that makes them distinctive.
"""

from __future__ import annotations

import dataclasses
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from mn_encounter_toolkit.generator.entities import (
    generate_address,
    generate_encounter_id,
    generate_icn,
    generate_mco,
    generate_member,
    generate_patient_account_number,
    generate_provider,
)
from mn_encounter_toolkit.models.core import MCO, Member, Provider
from mn_encounter_toolkit.models.encounter import (
    Diagnosis,
    Encounter,
    EPSDTInfo,
    InstitutionalDetail,
    MCOAdjudication,
    ServiceLine,
)
from mn_encounter_toolkit.refdata.diagnoses import DIAGNOSIS_POOL, DxRef, category_pool as dx_category_pool
from mn_encounter_toolkit.refdata.procedures import (
    ICD10_PCS_POOL,
    PROCEDURE_POOL,
    REVENUE_CODE_POOL,
    ProcedureRef,
)

CENTS = Decimal("0.01")


def q2(amount: Decimal) -> Decimal:
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def pick_weighted_dx(rng: random.Random, pool: Sequence[DxRef] = DIAGNOSIS_POOL, k: int = 1) -> list[DxRef]:
    return rng.choices(pool, weights=[d.weight for d in pool], k=k)


def pick_weighted_proc(rng: random.Random, pool: Sequence[ProcedureRef], k: int = 1) -> list[ProcedureRef]:
    return rng.choices(pool, weights=[p.weight for p in pool], k=k)


def build_diagnoses(rng: random.Random, *, n: int = 2, institutional: bool = False) -> tuple[Diagnosis, ...]:
    refs = pick_weighted_dx(rng, k=n)
    diagnoses = []
    for i, ref in enumerate(refs):
        poa = rng.choice(("Y", "N", "U", "W")) if institutional else None
        diagnoses.append(Diagnosis(code=ref.code, is_principal=(i == 0), poa_indicator=poa))
    return tuple(diagnoses)


def split_amount_by_weight(total: Decimal, weights: Sequence[Decimal]) -> list[Decimal]:
    """Split `total` across len(weights) buckets proportional to `weights`,
    guaranteeing the parts sum exactly to `total` (remainder goes to the
    last bucket) -- this is what keeps Layer 4 charge-balancing checks
    satisfied by construction for clean scenarios."""
    weight_total = sum(weights)
    if weight_total == 0 or total == 0:
        return [Decimal("0.00") for _ in weights]
    parts: list[Decimal] = []
    running = Decimal("0.00")
    for w in weights[:-1]:
        share = q2(total * w / weight_total)
        parts.append(share)
        running += share
    parts.append(q2(total - running))
    return parts


def build_professional_service_lines(
    rng: random.Random,
    diagnoses: tuple[Diagnosis, ...],
    *,
    n: int = 2,
    mco_paid_total: Decimal | None = None,
    service_date: date | None = None,
) -> tuple[ServiceLine, ...]:
    procs = pick_weighted_proc(rng, PROCEDURE_POOL, k=n)
    base_date = service_date or (date.today() - timedelta(days=rng.randint(5, 60)))
    charges = [q2(p.typical_charge * Decimal(str(rng.uniform(0.85, 1.15)))) for p in procs]
    paid_amounts = (
        split_amount_by_weight(mco_paid_total, charges) if mco_paid_total is not None else [None] * n
    )
    lines = []
    n_dx = len(diagnoses)
    for i, (proc, charge, paid) in enumerate(zip(procs, charges, paid_amounts), start=1):
        pointer_count = min(2, n_dx) if n_dx else 0
        pointers = tuple(range(1, pointer_count + 1)) if pointer_count else ()
        lines.append(
            ServiceLine(
                line_number=i,
                procedure_code=proc.code,
                modifiers=(),
                charge_amount=charge,
                units=Decimal("1"),
                service_date=base_date,
                diagnosis_pointers=pointers,
                mco_paid_amount_line=paid,
                allowed_amount_line=charge if paid is None else paid,
                paid_units=Decimal("1.00") if paid is not None else None,
            )
        )
    return tuple(lines)


def build_institutional_service_lines(
    rng: random.Random,
    diagnoses: tuple[Diagnosis, ...],
    *,
    n: int = 2,
    mco_paid_total: Decimal | None = None,
    service_date: date | None = None,
) -> tuple[ServiceLine, ...]:
    revs = pick_weighted_proc(rng, REVENUE_CODE_POOL, k=n)
    base_date = service_date or (date.today() - timedelta(days=rng.randint(5, 60)))
    charges = [q2(r.typical_charge * Decimal(str(rng.uniform(0.85, 1.15)))) for r in revs]
    paid_amounts = (
        split_amount_by_weight(mco_paid_total, charges) if mco_paid_total is not None else [None] * n
    )
    lines = []
    n_dx = len(diagnoses)
    for i, (rev, charge, paid) in enumerate(zip(revs, charges, paid_amounts), start=1):
        pointer_count = min(1, n_dx) if n_dx else 0
        pointers = tuple(range(1, pointer_count + 1)) if pointer_count else ()
        lines.append(
            ServiceLine(
                line_number=i,
                procedure_code=None,
                modifiers=(),
                charge_amount=charge,
                units=Decimal("1"),
                service_date=base_date,
                diagnosis_pointers=pointers,
                revenue_code=rev.code,
                mco_paid_amount_line=paid,
                allowed_amount_line=charge if paid is None else paid,
                paid_units=Decimal("1.00") if paid is not None else None,
            )
        )
    return tuple(lines)


def allocate_mco_paid(lines: tuple[ServiceLine, ...], mco_paid_total: Decimal) -> tuple[ServiceLine, ...]:
    """Distribute `mco_paid_total` across already-built `lines` proportional
    to each line's charge amount, without re-drawing any randomness -- use
    this instead of rebuilding lines so the procedure/charge draw and the
    paid-amount allocation are independent concerns."""
    charges = [line.charge_amount for line in lines]
    paid_amounts = split_amount_by_weight(mco_paid_total, charges)
    updated = []
    for line, paid in zip(lines, paid_amounts):
        updated.append(
            dataclasses.replace(
                line,
                mco_paid_amount_line=paid,
                allowed_amount_line=line.charge_amount,
                paid_units=Decimal("1.00"),
            )
        )
    return tuple(updated)


def build_mco_adjudication(
    *,
    paid_amount: Decimal,
    denied: bool = False,
    remaining_patient_liability: Decimal = Decimal("0.00"),
    non_covered_amount: Decimal = Decimal("0.00"),
) -> MCOAdjudication:
    return MCOAdjudication(
        paid_amount=paid_amount,
        remaining_patient_liability=remaining_patient_liability,
        non_covered_amount=non_covered_amount,
        # SOURCE: dhs_837_encounter_companion_guide.pdf p.24 -- "SBR09 ...
        # HM ... SEND ON DENIED CLAIMS/LINES ONLY. This is only for the
        # first occurrence."
        claim_filing_indicator="HM" if denied else "MC",
        payer_responsibility_code="U",
    )


def base_actors(
    rng: random.Random,
    *,
    program: str | None = None,
    with_tpl: bool = False,
    billing_atypical: bool = False,
    rendering_atypical: bool | None = None,
    separate_rendering_provider: bool = False,
) -> tuple[MCO, Provider, Provider, Member]:
    mco = generate_mco(rng)
    billing_provider = generate_provider(rng, is_atypical=billing_atypical)
    if separate_rendering_provider:
        rendering_atypical = billing_atypical if rendering_atypical is None else rendering_atypical
        rendering_provider = generate_provider(rng, is_atypical=rendering_atypical, is_organization=False)
    else:
        rendering_provider = billing_provider
    member = generate_member(rng, program=program, with_tpl=with_tpl)
    return mco, billing_provider, rendering_provider, member


def institutional_detail(
    rng: random.Random,
    *,
    admit_days_ago: int = 10,
    length_of_stay: int = 3,
) -> InstitutionalDetail:
    admission_date = date.today() - timedelta(days=admit_days_ago)
    discharge_date = admission_date + timedelta(days=length_of_stay)
    pcs = rng.choice(ICD10_PCS_POOL)
    return InstitutionalDetail(
        admission_date=admission_date,
        admission_hour="0800",
        discharge_date=discharge_date,
        discharge_hour="1400",
        admission_type_code=rng.choice(("1", "2", "3")),  # emergency/urgent/elective
        admission_source_code=rng.choice(("1", "2", "7")),  # physician referral/clinic/ER
        patient_status_code="01",  # discharged to home
        statement_from=admission_date,
        statement_through=discharge_date,
        drg_code=f"{rng.randint(1, 999):03d}",
        principal_procedure_code=pcs,
        patient_account_number=generate_patient_account_number(rng),
    )


def epsdt_info(rng: random.Random, *, referral_given: bool | None = None) -> EPSDTInfo:
    if referral_given is None:
        referral_given = rng.random() < 0.7
    condition = "NU" if not referral_given else rng.choice(("AV", "S2", "ST"))
    return EPSDTInfo(referral_given=referral_given, condition_indicator=condition)
