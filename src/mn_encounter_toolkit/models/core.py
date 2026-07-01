"""Core entity models: MCO, Provider, Member, and supporting value objects.

These are the "who" of an encounter -- the submitter (MCO), the rendering/
billing providers, and the MCO-enrolled member. Encounter-specific records
(claims, service lines, diagnoses) live in models/encounter.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

ProgramCode = Literal["PMAP", "MinnesotaCare", "MSHO", "MSC+", "SNBC"]

# SOURCE: dhs_837_encounter_companion_guide.pdf -- p.16 (837P) / p.40 (837I),
# Loop 2010BB NM1: payer name is always "MN DEPT OF HUMAN SERVICES", NM109
# (DHS Payer ID) is the fixed value "411674742". This is DHS's own real,
# publicly-documented EDI receiver identity (not a synthetic/PII value), used
# as a constant so generated files match the documented receiver. ISA08/GS03
# use the hyphenated FEIN form "41-1674742" per the Envelope Information
# section (p.35-36).
DHS_PAYER_ID = "411674742"
DHS_RECEIVER_FEIN_HYPHENATED = "41-1674742"
DHS_PAYER_NAME = "MN DEPT OF HUMAN SERVICES"


@dataclass(frozen=True)
class MNAddress:
    """A Minnesota service/mailing address. Street-level details are always
    fictional; city/county/ZIP combinations are drawn from real MN geography
    (see refdata/mn_geo.py) so addresses are realistic without being real
    street addresses tied to real people or businesses."""

    line1: str
    city: str
    county: str
    zip5: str
    state: str = "MN"


@dataclass(frozen=True)
class MCO:
    """A Managed Care Organization submitting encounters to DHS.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- Envelope Information,
    p.35 ("ISA06 ... THIS MUST CHANGE TO THE 10-DIGIT NATIONAL PROVIDER
    IDENTIFIER (NPI) OR UNIVERSAL MINNESOTA PROVIDER IDENTIFIER (UMPI)
    FOLLOWED BY 5 TRAILING SPACES" and "GS02 ... MUST MATCH THE NUMBER IN
    ISA06 WITHOUT THE TRAILING SPACES"). The MCO is the ISA/GS *submitter*,
    never the rendering provider -- trading_partner_id is what is written to
    ISA06 (padded to 15) / GS02 (unpadded, 10 chars), not any provider
    identifier from the inner loops.
    """

    trading_partner_id: str  # 10-char NPI- or UMPI-shaped id, ISA06/GS02
    payer_id: str  # MCO's own internal payer id (used in member's other MCO refs)
    name: str
    programs: tuple[ProgramCode, ...]
    counties: tuple[str, ...]


@dataclass(frozen=True)
class Provider:
    """A rendering, billing, referring, or supervising provider.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- Loop 2010AA (p.13-14,
    837P; p.37-38, 837I): NPI is conditional (C1) at NM108/NM109; TIN is
    required (Y) at REF*EI regardless of NPI presence. Loop 2310B/2310A/
    2310D/2310C (p.20-22): UMPI is sent as a *secondary* identifier via
    REF*G2 ("PROVIDER COMMERCIAL NUMBER" qualifier; DHS repurposes G2 to
    carry the UMPI). Atypical providers (no NPI under MN statute) omit
    NM108/NM109 entirely and rely on REF*EI (TIN) as their only "primary"
    identifier, with REF*G2 (UMPI) still present as secondary.
    """

    name_last: str
    name_first: str | None  # None for organizational (non-person) providers
    is_organization: bool
    npi: str | None  # None only when is_atypical is True
    umpi: str
    tin: str
    taxonomy_code: str
    is_atypical: bool
    address: MNAddress

    def __post_init__(self) -> None:
        if self.is_atypical and self.npi is not None:
            raise ValueError("Atypical providers must not carry an NPI (no NPI under MN statute).")
        if not self.is_atypical and self.npi is None:
            raise ValueError("Standard (non-atypical) providers must carry an NPI.")


@dataclass(frozen=True)
class TPLPayer:
    """A third-party-liability payer reported in the encounter's COB loop.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- Loop 2320/2330B (p.23-26,
    837P): "IF THE PRIMARY PAYER IS A THIRD PARTY, THE SECOND OCCURRENCE OF
    THIS SEGMENT SHOULD CONTAIN A 'P' [SBR01] AND INFORMATION RELATED TO THE
    RELEVANT THIRD PARTY PAYER. UP TO 10 SBR LOOPS CAN BE SENT." This models
    that second-or-later SBR/2330B occurrence; it is independent of (and in
    addition to) the MCO's own mandatory first-occurrence adjudication info
    (see models/encounter.py: Encounter.mco_adjudication).
    """

    payer_name: str
    payer_id: str
    paid_amount: Decimal
    remaining_patient_liability: Decimal
    non_covered_amount: Decimal
    claim_filing_indicator: str  # SBR09, e.g. "CI" commercial, "MA" Medicare Part A
    payer_responsibility_code: str = "P"  # SBR01: P=primary, S=secondary, T=tertiary


@dataclass(frozen=True)
class Member:
    """An MCO-enrolled MHCP member (the subscriber/patient).

    SOURCE: dhs_837_encounter_companion_guide.pdf -- Loop 2010BA (p.14-15,
    837P; p.39, 837I): "NM109 ... DHS ASSIGNED EIGHT DIGIT MEMBER ID". The
    member is always the subscriber under MHCP (SBR02=18 "Self"), never a
    dependent.
    """

    medicaid_id: str  # 8-digit DHS-assigned member ID (NM109, loop 2010BA)
    mco_member_id: str  # MCO's own member number (REF*Y4, loop 2010BA)
    first_name: str
    last_name: str
    dob: date
    gender: Literal["M", "F", "U"]
    county: str
    program: ProgramCode
    tpl: TPLPayer | None = None  # None when member has no other insurance

    @property
    def has_tpl(self) -> bool:
        return self.tpl is not None
