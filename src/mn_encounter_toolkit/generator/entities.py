"""Seeded generation of MCOs, providers, members, and supporting identifiers.

Every function here takes an explicit `random.Random` instance (never the
global `random` module) so callers control determinism end-to-end.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from mn_encounter_toolkit.identifiers.npi import generate_npi
from mn_encounter_toolkit.identifiers.tin import generate_tin
from mn_encounter_toolkit.identifiers.umpi import generate_umpi
from mn_encounter_toolkit.models.core import MCO, Member, MNAddress, Provider, TPLPayer
from mn_encounter_toolkit.refdata.mn_geo import MN_CITIES, STREET_NAMES, STREET_SUFFIXES, MNCity
from mn_encounter_toolkit.refdata.payers import (
    FICTIONAL_MCO_NAMES,
    PROGRAM_CODES,
    TPL_PAYER_POOL,
)

_FIRST_NAMES = (
    "Avery", "Jordan", "Riley", "Casey", "Morgan", "Quinn", "Hayden", "Skylar",
    "Rowan", "Emerson", "Logan", "Parker", "Finley", "Sawyer", "Dakota",
    "Reese", "Elliot", "Marlowe", "Greer", "Wren",
)
_LAST_NAMES = (
    "Lindqvist", "Norgren", "Halvorsen", "Bergstrom", "Olafson", "Running Cloud",
    "Kowalczyk", "Mbeki", "Vang", "Yang", "Hernandez-Reyes", "Okafor",
    "Whitebird", "Lindstrom", "Carriveau", "Desjarlait", "Anderson", "Lindgren",
)
_ORG_PROVIDER_NAMES = (
    "Northwoods Family Clinic",
    "Prairie River Behavioral Health",
    "Twin Lakes Community Health Center",
    "Mississippi Bluffs Rehabilitation",
    "Anishinaabe Wellness Center",
)

def fictional_street_address(rng: random.Random) -> str:
    number = rng.randint(100, 9999)
    name = rng.choice(STREET_NAMES)
    suffix = rng.choice(STREET_SUFFIXES)
    return f"{number} {name} {suffix}"


def random_mn_city(rng: random.Random, region: str | None = None) -> MNCity:
    pool = MN_CITIES if region is None else tuple(c for c in MN_CITIES if c.region == region)
    return rng.choice(pool)


def generate_address(rng: random.Random, *, region: str | None = None) -> MNAddress:
    city = random_mn_city(rng, region=region)
    return MNAddress(
        line1=fictional_street_address(rng),
        city=city.city,
        county=city.county,
        zip5=city.zip5,
    )


def generate_mco(rng: random.Random, *, name: str | None = None) -> MCO:
    mco_name = name or rng.choice(FICTIONAL_MCO_NAMES)
    counties = tuple(sorted({random_mn_city(rng).county for _ in range(rng.randint(3, 6))}))
    programs = tuple(rng.sample(PROGRAM_CODES, k=rng.randint(2, len(PROGRAM_CODES))))
    return MCO(
        # SOURCE: dhs_837_encounter_companion_guide.pdf p.35 -- ISA06/GS02
        # carry a 10-digit NPI-or-UMPI-shaped trading partner id for the
        # submitter (the MCO). MCOs are not individually NPI-enrolled
        # providers, so this is modeled as an 8-digit UMPI-shaped id
        # zero-padded to 10 characters at write time (see edi/writer.py).
        trading_partner_id=generate_umpi(rng),
        payer_id="".join(str(rng.randint(0, 9)) for _ in range(7)),
        name=mco_name,
        programs=programs,
        counties=counties,
    )


def generate_provider(
    rng: random.Random,
    *,
    is_atypical: bool = False,
    is_organization: bool | None = None,
) -> Provider:
    if is_organization is None:
        is_organization = rng.random() < 0.35
    if is_organization:
        name_last = rng.choice(_ORG_PROVIDER_NAMES)
        name_first = None
    else:
        name_last = rng.choice(_LAST_NAMES)
        name_first = rng.choice(_FIRST_NAMES)
    return Provider(
        name_last=name_last,
        name_first=name_first,
        is_organization=is_organization,
        npi=None if is_atypical else generate_npi(rng, is_organization=is_organization),
        umpi=generate_umpi(rng),
        tin=generate_tin(rng),
        taxonomy_code=rng.choice(
            ("103T00000X", "2084P0800X", "261QM0801X", "251E00000X", "291U00000X")
        ),
        is_atypical=is_atypical,
        address=generate_address(rng),
    )


def generate_member(
    rng: random.Random,
    *,
    program: str | None = None,
    with_tpl: bool = False,
) -> Member:
    city = random_mn_city(rng)
    dob = date(1950, 1, 1) + timedelta(days=rng.randint(0, 365 * 70))
    tpl = None
    if with_tpl:
        ref = rng.choices(TPL_PAYER_POOL, weights=[t.weight for t in TPL_PAYER_POOL], k=1)[0]
        tpl = TPLPayer(
            payer_name=ref.name,
            payer_id="".join(str(rng.randint(0, 9)) for _ in range(7)),
            paid_amount=Decimal("0.00"),
            remaining_patient_liability=Decimal("0.00"),
            non_covered_amount=Decimal("0.00"),
            claim_filing_indicator=ref.claim_filing_indicator,
        )
    return Member(
        medicaid_id="".join(str(rng.randint(0, 9)) for _ in range(8)),
        mco_member_id="".join(str(rng.randint(0, 9)) for _ in range(9)),
        first_name=rng.choice(_FIRST_NAMES),
        last_name=rng.choice(_LAST_NAMES),
        dob=dob,
        gender=rng.choice(("M", "F", "U")),
        county=city.county,
        program=program or rng.choice(PROGRAM_CODES),
        tpl=tpl,
    )


def generate_icn(rng: random.Random) -> str:
    """An 8-digit MCO-assigned Internal Control Number (ICN).

    SOURCE: dhs_837_encounter_companion_guide.pdf -- CLM01 ("MCO'S OWN CLAIM
    NUMBER (ICN)"), and the NTE/REF correction-tracking format example
    "C=12345678" (p.19, p.44), which is 8 digits.
    """
    return "".join(str(rng.randint(0, 9)) for _ in range(8))


def generate_encounter_id(rng: random.Random, *, prefix: str = "ENC") -> str:
    """A seeded, reproducible internal encounter id (distinct from the
    X12 ICN, though both are derived from the same seeded rng stream)."""
    return f"{prefix}{''.join(str(rng.randint(0, 9)) for _ in range(8))}"


def generate_patient_account_number(rng: random.Random) -> str:
    """837I NTE*UPI value: PAC= plus eight digits.

    SOURCE: dhs_837_encounter_companion_guide.pdf p.44 (837I) -- patient
    account number required on all 837I claims via NTE01=UPI.
    """
    return f"PAC={''.join(str(rng.randint(0, 9)) for _ in range(8))}"
