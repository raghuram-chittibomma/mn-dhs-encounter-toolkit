"""Encounter-specific models: the claim itself, its lines, diagnoses, and
institutional detail. See models/core.py for the MCO/Provider/Member "who".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from mn_encounter_toolkit.models.core import MCO, Member, Provider, TPLPayer

ClaimType = Literal["837P", "837I"]

# SOURCE: dhs_837_encounter_companion_guide.pdf -- p.17 (837P CLM05-3) and
# p.41 (837I CLM05-3). The DHS guide's own CLM05-3 value tables list only
# "1" (Original / Admit-thru-discharge) and "8" (Void); "7" (Replacement) is
# NOT enumerated in either table. The task spec for this project explicitly
# defines replacement encounters as CLM05-3=7 (standard base X12 837 IG
# convention). This is a genuine conflict between the spec's instructions and
# the retrieved DHS guide's literal documented value set.
#
# Resolution (flagged in KNOWN_LIMITATIONS.md):
#   - We keep "7" as the FrequencyCode value for replacement encounters, per
#     the spec's explicit instruction, since CLM05-3=7 is valid base-X12-IG
#     syntax and DHS does not say it is *prohibited* -- only that its own
#     example tables don't show it.
#   - We ALSO emit the DHS-documented correction-tracking mechanism (NTE
#     segment, NTE01=ADD, NTE02="C=<original ICN>") that the guide explicitly
#     requires for "a corrected version of a DHS denied claim or voided
#     claim" (p.19, 837P; p.44, 837I), in addition to setting CLM05-3=7.
#   - Void encounters (CLM05-3=8) use the guide's explicitly-confirmed
#     mechanism: REF segment, REF01=F8, REF02=original ICN (p.19, 837P;
#     p.43, 837I), which is unambiguous and not in conflict with anything.
FrequencyCode = Literal["1", "7", "8"]


@dataclass(frozen=True)
class Diagnosis:
    """One HI-segment diagnosis code.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- p.20 (837P HI segment):
    HI01-1="ABK" for the principal (first) diagnosis, "ABF" for every
    subsequent diagnosis (ICD-10-CM throughout; "Do not send decimal points
    in the diagnosis code."). For 837I, principal/other diagnosis carry an
    additional POA indicator (p.45-47, HI01-9 / HI02-9..HI12-9): N/U/W/Y.
    """

    code: str  # ICD-10-CM, no decimal point, e.g. "F1120"
    is_principal: bool = False
    poa_indicator: Literal["N", "U", "W", "Y"] | None = None  # 837I only


@dataclass(frozen=True)
class ServiceLine:
    """One 2400-loop service line.

    SOURCE: dhs_837_encounter_companion_guide.pdf:
      - SV101-2 (837P, p.27) / revenue code (837I): the billed procedure.
      - SV102 (837P) line charge amount.
      - SV107 (837P, p.27) composite diagnosis code pointer -- up to 4
        1-based pointers into the claim's HI/Diagnosis list.
      - REF*9B / REF*9D (837P p.28 and 837I p.59): line-level allowed /
        paid amount.
      - AMT*T (837P) / AMT*GT (837I) (changelog 06/26/2024): paid units,
        format XXX.00.
    """

    line_number: int
    procedure_code: str | None  # CPT/HCPCS (837P, SV101-2); None for 837I
    modifiers: tuple[str, ...]
    charge_amount: Decimal
    units: Decimal
    service_date: date
    diagnosis_pointers: tuple[int, ...]  # 1-based indices into Encounter.diagnoses
    revenue_code: str | None = None  # 837I institutional revenue code
    mco_paid_amount_line: Decimal | None = None  # REF*9D at line level (837P and 837I)
    allowed_amount_line: Decimal | None = None  # REF*9B at line level (837P and 837I)
    paid_units: Decimal | None = None  # AMT*T / AMT*GT


@dataclass(frozen=True)
class EPSDTInfo:
    """EPSDT / Teen Checkup (Child and Teen Checkup, C&TC) referral info.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- p.19 (837P CRC segment)
    / p.44-45 (837I CRC segment), "EPSDT REFERRAL"/"C&TC REFERRAL":
    CRC01="ZZ" (mutually defined), CRC02 = Y/N (was a referral given),
    CRC03 condition indicator: AV (available, not used -- patient refused),
    NU (not used -- required when CRC02=N), S2 (under treatment), ST (new
    services requested/referred).
    """

    referral_given: bool  # CRC02
    condition_indicator: Literal["AV", "NU", "S2", "ST"]  # CRC03

    def __post_init__(self) -> None:
        # SOURCE: dhs_837_encounter_companion_guide.pdf p.19/p.45 -- "NU ...
        # MUST BE USED WHEN THE SUBMITTER ANSWERS 'N' IN CRC02."
        if not self.referral_given and self.condition_indicator != "NU":
            raise ValueError("CRC03 must be 'NU' whenever CRC02 (referral_given) is No.")


@dataclass(frozen=True)
class InstitutionalDetail:
    """837I-only claim detail: admission/discharge, statement period, and
    institutional claim codes.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- p.41-43: DTP*096
    (discharge hour), DTP*434 (statement dates, RD8), DTP*435 (admission
    date/hour, format CCYYMMDDHHMM), CL1 segment (CL101 admission type,
    CL102 admission source, CL103 patient status).
    """

    admission_date: date
    admission_hour: str  # HHMM, part of DTP*435 (CCYYMMDDHHMM)
    discharge_date: date
    discharge_hour: str  # HHMM, DTP*096 ("can be defaulted to 00")
    admission_type_code: str  # CL101
    admission_source_code: str  # CL102
    patient_status_code: str  # CL103, NUBC patient status code list 239
    statement_from: date  # DTP*434 RD8 from
    statement_through: date  # DTP*434 RD8 through
    # SOURCE: dhs_837_encounter_companion_guide.pdf p.43-44 (837I loop 2300) --
    # claim-level allowed/paid when reporting an inpatient total (REF*9A/9C).
    # Omit when paid amounts are reported only at the 2400 line level (REF*9B/9D).
    mco_paid_amount_claim: Decimal | None = None  # REF*9C at 2300
    allowed_amount_claim: Decimal | None = None  # REF*9A at 2300
    # SOURCE: dhs_837_encounter_companion_guide.pdf p.47-48 -- HI segment,
    # HI01-1="BBR" principal procedure (ICD-10-PCS) / "BBQ" other procedure.
    # DRG itself was not found in the 837I encounter section of the
    # retrieved guide (it appears instead in the 835/remittance side --
    # mucg_835.pdf Appendix E, "Reporting All Patients Refined DRG
    # (APR-DRG)"). DRG is therefore tracked here only as informational
    # metadata for synthetic realism, not as a field the writer maps to a
    # specific 837I segment.
    # TODO: VERIFY AGAINST dhs_837_encounter_companion_guide.pdf -- if DHS
    # does expect DRG on the *encounter* (not just the 835E response), find
    # the exact segment/element before treating this as anything other than
    # informational.
    drg_code: str | None = None
    principal_procedure_code: str | None = None  # HI01-1=BBR, ICD-10-PCS
    other_procedure_codes: tuple[str, ...] = ()  # HI01-1=BBQ, ICD-10-PCS

    def __post_init__(self) -> None:
        if self.discharge_date < self.admission_date:
            raise ValueError("discharge_date must be on or after admission_date.")


@dataclass(frozen=True)
class MCOAdjudication:
    """The MANDATORY first occurrence of loop 2320/2330: the MCO reporting
    its own adjudication as a payer. This is required on every encounter,
    independent of whether a third-party payer (TPL) is also present.

    SOURCE: dhs_837_encounter_companion_guide.pdf -- p.23 (837P): "2320 ...
    THIS LOOP IS REQUIRED -- THE FIRST OCCURRENCE MUST CONTAIN INFORMATION
    FOR THE MCO AS THE PRIMARY/SECONDARY PAYER. IF THE PRIMARY PAYER IS A
    THIRD PARTY, THE SECOND OCCURRENCE OF THIS SEGMENT SHOULD CONTAIN A 'P'
    ... UP TO 10 SBR LOOPS CAN BE SENT." SBR09="HM" is specified as "send on
    denied claims/lines only" for this first occurrence (p.24); AMT*D/
    AMT*EAF/AMT*A8 carry payer-paid amount, remaining patient liability, and
    non-covered amount respectively (p.24-25).
    """

    paid_amount: Decimal  # AMT*D02 ("PAYER PAID AMOUNT; ZERO IS ACCEPTABLE")
    remaining_patient_liability: Decimal = Decimal("0.00")  # AMT*EAF02
    non_covered_amount: Decimal = Decimal("0.00")  # AMT*A802
    claim_filing_indicator: str = "MC"  # SBR09: "MC" normal, "HM" if denied
    payer_responsibility_code: str = "U"  # SBR01: U=unknown is DHS's own default


@dataclass(frozen=True)
class Encounter:
    """A single 837P or 837I encounter record -- the unit the generator
    produces and the writer turns into an X12 transaction set (one ST/SE).
    """

    encounter_id: str  # internal id; also seeds CLM01 (MCO's own ICN)
    claim_type: ClaimType
    frequency_code: FrequencyCode  # CLM05-3
    original_icn: str | None  # required when frequency_code in {"7", "8"}
    mco: MCO
    billing_provider: Provider
    rendering_provider: Provider
    member: Member
    total_charge_amount: Decimal  # CLM02
    mco_paid_amount: Decimal | None  # header-level summary of MCO-paid amount
    mco_adjudication: MCOAdjudication
    diagnoses: tuple[Diagnosis, ...]
    service_lines: tuple[ServiceLine, ...]
    place_of_service: str = "11"  # CLM05-1, POS code, 837P only
    tpl: TPLPayer | None = None  # second+ occurrence of loop 2320, if present
    epsdt: EPSDTInfo | None = None
    institutional: InstitutionalDetail | None = None
    referring_provider: Provider | None = None
    scenario_name: str = ""

    def __post_init__(self) -> None:
        # Only structural (always-true-for-any-legitimate-claim) invariants
        # are enforced here. Business-rule invariants that the err_* fixture
        # scenarios must be able to deliberately violate (e.g. "void/
        # replacement requires original_icn", "charge totals balance") live
        # in generator/consistency.py instead, which is opt-out-able for
        # those specific, clearly-marked fixtures. See generator/scenarios/
        # errors.py.
        if self.claim_type == "837I" and self.institutional is None:
            raise ValueError("837I encounters require institutional detail.")
        if self.claim_type == "837P" and self.institutional is not None:
            raise ValueError("837P encounters must not carry institutional detail.")
