"""837P / 837I writer: Encounter records -> X12 text.

Every segment-building function below carries a SOURCE comment citing the
exact page/loop/segment of dhs_837_encounter_companion_guide.pdf it maps
from, per the spec's auditability requirement. Page numbers refer to the
"-- N of 90 --" page markers embedded in the PDF text layer.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Sequence

from mn_encounter_toolkit.edi.x12_core import DEFAULT_SEPARATORS, Separators, build_segment
from mn_encounter_toolkit.generator.consistency import InconsistentEncounterError, find_inconsistencies
from mn_encounter_toolkit.models.core import DHS_PAYER_ID, DHS_PAYER_NAME, DHS_RECEIVER_FEIN_HYPHENATED, Provider
from mn_encounter_toolkit.models.encounter import Encounter

# SOURCE: dhs_837_encounter_companion_guide.pdf p.35/p.36 -- GS08 value per
# transaction type.
_GS08_BY_CLAIM_TYPE = {"837P": "005010X222A1", "837I": "005010X223A2"}
_ST03_BY_CLAIM_TYPE = {"837P": "005010X222A1", "837I": "005010X223A2"}

# A scenario carrying this name signals the writer to deliberately corrupt
# IEA02 so it no longer matches ISA13 -- see generator/scenarios/errors.py.
ERR_BAD_ENVELOPE_SCENARIO = "err_bad_envelope"


class EnvelopeBuilder:
    """Accumulates segments for one ISA..IEA interchange and tracks the
    counters (segment counts, control numbers) needed for the trailer
    segments (SE/GE/IEA)."""

    def __init__(self, separators: Separators) -> None:
        self.separators = separators
        self.segments: list[str] = []

    def add(self, *elements: str | tuple[str, ...]) -> None:
        self.segments.append(build_segment(self.separators, *elements))

    def text(self) -> str:
        # A newline after every terminated segment is not required by X12,
        # but it is what gives Layer 1/2/3/4 findings a meaningful "line
        # number" to report (see edi/parser.py), and matches common
        # real-world EDI file formatting.
        return "\n".join(self.segments) + "\n"


def _fmt_money(amount: Decimal | None) -> str:
    if amount is None:
        return ""
    return f"{amount:.2f}"


def _fmt_date(d: _dt.date) -> str:
    return d.strftime("%Y%m%d")


def _provider_name_elements(provider: Provider) -> tuple[str, str, str]:
    entity_qualifier = "2" if provider.is_organization else "1"
    last = provider.name_last
    first = provider.name_first or ""
    return entity_qualifier, last, first


def write_billing_provider_loop(env: EnvelopeBuilder, billing: Provider) -> None:
    # SOURCE: p.13-14 (837P) / p.37-38 (837I) -- PRV (taxonomy), 2010AA NM1
    # (NM108/109 NPI is conditional C1), N3/N4 (address), REF*EI (TIN,
    # required Y), REF*G2 (UMPI secondary, conditional C1).
    env.add("PRV", "BI", "PXC", billing.taxonomy_code)
    qualifier, last, first = _provider_name_elements(billing)
    if billing.npi:
        env.add("NM1", "85", qualifier, last, first, "", "", "", "XX", billing.npi)
    else:
        # Atypical provider: no NPI under MN statute -- NM108/NM109 omitted.
        env.add("NM1", "85", qualifier, last, first)
    env.add("N3", billing.address.line1)
    env.add("N4", billing.address.city, billing.address.state, billing.address.zip5)
    env.add("REF", "EI", billing.tin)
    if billing.umpi:
        # SOURCE: p.16 (837P) / p.40 (837I) -- REF*G2 "(REPLACES 2010AA PAY
        # TO PROVIDER UMPI) PROVIDER COMMERCIAL NUMBER" / "BILLING PROVIDER
        # SECONDARY IDENTIFIER (DHS UMPI NUMBER)".
        env.add("REF", "G2", billing.umpi)
    # else: deliberately omitted -- see generator/scenarios/errors.py err_missing_umpi.


def write_referring_rendering_loops(
    env: EnvelopeBuilder, *, rendering: Provider, billing: Provider, referring: Provider | None
) -> None:
    # SOURCE: p.21-22 (837P), Loop 2310A (referring, C1) / 2310B (rendering,
    # C2 "REQUIRED WHEN RENDERING PROVIDER INFORMATION IS DIFFERENT THAN
    # PROVIDER LISTED IN LOOP 2010AA"). REF*G2 carries UMPI as secondary id
    # in both loops.
    if referring is not None:
        q, last, first = _provider_name_elements(referring)
        env.add("NM1", "DN", q, last, first, "", "", "", "XX", referring.npi or "")
        if referring.umpi:
            env.add("REF", "G2", referring.umpi)
    if rendering != billing:
        q, last, first = _provider_name_elements(rendering)
        if rendering.npi:
            env.add("NM1", "82", q, last, first, "", "", "", "XX", rendering.npi)
        else:
            env.add("NM1", "82", q, last, first)
        if rendering.umpi:
            env.add("REF", "G2", rendering.umpi)


def write_subscriber_loop(env: EnvelopeBuilder, encounter: Encounter) -> None:
    member = encounter.member
    # SOURCE: p.14-15 (837P) / p.39 (837I) -- SBR01=U, SBR02=18 (Self,
    # MHCP member is always the subscriber), SBR09=MC (Medicaid).
    env.add("SBR", "U", "18", "", "", "", "", "", "", "MC")
    env.add(
        "NM1", "IL", "1", member.last_name, member.first_name, "", "", "", "MI", member.medicaid_id
    )
    env.add("N3", "N/A")
    env.add("N4", "N/A", "N/A", "00000")
    env.add("DMG", "D8", _fmt_date(member.dob), member.gender)
    env.add("REF", "Y4", member.mco_member_id)
    # SOURCE: p.15-16 (837P) / p.40 (837I), Loop 2010BB -- payer is always
    # DHS itself; NM108=PI, NM109=411674742 (DHS_PAYER_ID).
    env.add("NM1", "PR", "2", DHS_PAYER_NAME, "", "", "", "", "PI", DHS_PAYER_ID)


def write_claim_segments(env: EnvelopeBuilder, encounter: Encounter) -> None:
    if encounter.claim_type == "837P":
        # SOURCE: p.17 -- CLM05 composite: CLM05-1=POS, CLM05-2="B"
        # (professional/dental POS qualifier), CLM05-3=freq code.
        clm05 = (encounter.place_of_service, "B", encounter.frequency_code)
        clm06 = "Y"
    else:
        # SOURCE: p.41 -- CLM05-1=first 2 digits of UB bill type,
        # CLM05-2="A" (UB claim form bill type qualifier). CLM06 is "N/U"
        # ("THIS DATA ELEMENT IS NO LONGER USED") -- we send "N" as a
        # harmless placeholder per the guide's own fallback value list.
        bill_type = encounter.institutional.admission_type_code.rjust(2, "0") if encounter.institutional else "11"
        clm05 = (bill_type, "A", encounter.frequency_code)
        clm06 = "N"
    env.add(
        "CLM",
        encounter.encounter_id,
        _fmt_money(encounter.total_charge_amount),
        "",
        "",
        clm05,
        clm06,
        "A",
        "Y",
        "Y",
    )

    if encounter.institutional is not None:
        inst = encounter.institutional
        env.add("DTP", "434", "RD8", f"{_fmt_date(inst.statement_from)}-{_fmt_date(inst.statement_through)}")
        env.add(
            "DTP", "435", "DT", f"{_fmt_date(inst.admission_date)}{inst.admission_hour}"
        )
        env.add("DTP", "096", "TM", inst.discharge_hour)
        # SOURCE: p.42-43 -- CL1: CL101 admission type, CL102 admission
        # source, CL103 patient status.
        env.add("CL1", inst.admission_type_code, inst.admission_source_code, inst.patient_status_code)

    if encounter.frequency_code == "8" and encounter.original_icn:
        # SOURCE: p.19/p.43 -- REF*F8, void-only usage.
        env.add("REF", "F8", encounter.original_icn)
    elif encounter.frequency_code == "7" and encounter.original_icn:
        # SOURCE: p.19/p.44 -- NTE*ADD, "C=<ICN>" tracking format. See
        # models/encounter.py FrequencyCode docstring re: the source
        # document's CLM05-3 value-table ambiguity this resolves.
        env.add("NTE", "ADD", f"C={encounter.original_icn}")
    # else (frequency_code in {7,8} but original_icn falsy): deliberately
    # omit the segment entirely -- see generator/scenarios/errors.py
    # err_void_no_icn / err_replacement_no_icn, and Layer 4's
    # L4-VOID-REPLACEMENT-HAS-ICN, which flags exactly this omission.

    write_diagnoses(env, encounter)

    if encounter.epsdt is not None:
        # SOURCE: p.19 (837P) / p.44-45 (837I) -- CRC*ZZ*<Y/N>*<indicator>.
        crc02 = "Y" if encounter.epsdt.referral_given else "N"
        env.add("CRC", "ZZ", crc02, encounter.epsdt.condition_indicator)

    write_referring_rendering_loops(
        env,
        rendering=encounter.rendering_provider,
        billing=encounter.billing_provider,
        referring=encounter.referring_provider,
    )

    write_mco_adjudication_loop(env, encounter)


def write_diagnoses(env: EnvelopeBuilder, encounter: Encounter) -> None:
    institutional = encounter.institutional is not None
    for i, dx in enumerate(encounter.diagnoses):
        if i == 0:
            # SOURCE: p.20 (837P) / p.45 (837I) -- HI01-1="ABK" principal dx.
            qualifier = "ABK"
        else:
            # SOURCE: p.20 (837P) / p.47 (837I) -- HI01-1="ABF" other dx.
            qualifier = "ABF"
        if institutional and dx.poa_indicator:
            env.add("HI", (qualifier, dx.code, "", "", "", "", "", "", dx.poa_indicator))
        else:
            env.add("HI", (qualifier, dx.code))


def write_mco_adjudication_loop(env: EnvelopeBuilder, encounter: Encounter) -> None:
    # SOURCE: p.23-26 -- Loop 2320 first occurrence = MCO's own
    # adjudication (mandatory on every encounter); SBR01=U default,
    # AMT*D/AMT*EAF/AMT*A8 = paid/remaining-liability/non-covered.
    adj = encounter.mco_adjudication
    env.add(
        "SBR", adj.payer_responsibility_code, "18", "", "", "", "", "", "", adj.claim_filing_indicator
    )
    env.add("AMT", "D", _fmt_money(adj.paid_amount))
    env.add("AMT", "EAF", _fmt_money(adj.remaining_patient_liability))
    env.add("AMT", "A8", _fmt_money(adj.non_covered_amount))
    env.add("NM1", "IL", "1", encounter.member.last_name, encounter.member.first_name, "", "", "", "MI", encounter.member.medicaid_id)
    env.add("NM1", "PR", "2", DHS_PAYER_NAME, "", "", "", "", "PI", DHS_PAYER_ID)

    if encounter.tpl is not None:
        # SOURCE: p.23 -- second occurrence of 2320/SBR, SBR01="P" when the
        # third party is primary; up to 10 SBR loops total are allowed.
        tpl = encounter.tpl
        env.add("SBR", tpl.payer_responsibility_code, "18", "", "", "", "", "", "", tpl.claim_filing_indicator)
        env.add("AMT", "D", _fmt_money(tpl.paid_amount))
        env.add("AMT", "EAF", _fmt_money(tpl.remaining_patient_liability))
        env.add("AMT", "A8", _fmt_money(tpl.non_covered_amount))
        env.add("NM1", "IL", "1", encounter.member.last_name, encounter.member.first_name, "", "", "", "MI", "UNKNOWN")
        env.add("NM1", "PR", "2", tpl.payer_name, "", "", "", "", "PI", tpl.payer_id)


def write_service_lines(env: EnvelopeBuilder, encounter: Encounter) -> None:
    institutional = encounter.claim_type == "837I"
    for line in encounter.service_lines:
        env.add("LX", str(line.line_number))
        pointers = tuple(str(p) for p in line.diagnosis_pointers) or ("",)
        if institutional:
            # SOURCE: 837I uses SV2 (institutional service line); revenue
            # code in SV201, charge in SV203, units in SV205.
            env.add(
                "SV2",
                line.revenue_code or "",
                "",
                _fmt_money(line.charge_amount),
                "UN",
                str(line.units),
            )
        else:
            # SOURCE: p.27 -- SV1: SV101-1="HC", SV101-2=procedure code,
            # SV101-3..6=modifiers, SV102=charge, SV103="UN", SV104=units,
            # SV107=composite diagnosis pointer (up to 4, 1-based).
            sv101 = ("HC", line.procedure_code or "") + tuple(line.modifiers[:4])
            env.add(
                "SV1",
                sv101,
                _fmt_money(line.charge_amount),
                "UN",
                str(line.units),
                "",
                "",
                pointers,
            )
        env.add("DTP", "472", "D8", _fmt_date(line.service_date))
        if line.allowed_amount_line is not None:
            # SOURCE: p.28 (837P REF*9B) / p.43 (837I REF*9A) -- allowed
            # amount, line level.
            allowed_qualifier = "9A" if institutional else "9B"
            env.add("REF", allowed_qualifier, _fmt_money(line.allowed_amount_line))
        if line.mco_paid_amount_line is not None:
            # SOURCE: p.28 (837P REF*9D) / p.43 (837I REF*9C) -- "THE
            # AMOUNT PAID TO THE PROVIDER EXCLUDING THIRD PARTY LIABILITY,
            # PROVIDER WITHHOLDS, INCENTIVES, AND MEMBER COST SHARING".
            paid_qualifier = "9C" if institutional else "9D"
            env.add("REF", paid_qualifier, _fmt_money(line.mco_paid_amount_line))
        if line.paid_units is not None:
            # SOURCE: changelog 06/26/2024 -- AMT*T (837P) / AMT*GT (837I),
            # paid units, format XXX.00.
            paid_units_qualifier = "GT" if institutional else "T"
            env.add("AMT", paid_units_qualifier, f"{line.paid_units:.2f}")


def write_encounter_claim(env: EnvelopeBuilder, encounter: Encounter, *, hl_id: int) -> int:
    """Writes one full 2000A..2400 block for a single encounter, starting
    its billing-provider HL at `hl_id`. Returns the next free HL id."""
    billing_hl = hl_id
    subscriber_hl = hl_id + 1
    env.add("HL", str(billing_hl), "", "20", "1")
    write_billing_provider_loop(env, encounter.billing_provider)
    env.add("HL", str(subscriber_hl), str(billing_hl), "22", "0")
    write_subscriber_loop(env, encounter)
    write_claim_segments(env, encounter)
    write_service_lines(env, encounter)
    return subscriber_hl + 1


def write_transaction_set(
    encounters: Sequence[Encounter],
    *,
    separators: Separators,
    st_control_number: str,
    submission_date: _dt.date,
    submission_time: str = "0800",
) -> list[str]:
    """Build the ST..SE segments (as a list of pre-terminated strings) for
    one transaction set. All encounters must share the same claim_type."""
    claim_type = encounters[0].claim_type
    if any(e.claim_type != claim_type for e in encounters):
        raise ValueError("write_transaction_set requires all encounters to share one claim_type.")
    env = EnvelopeBuilder(separators)
    # SOURCE: p.12 (837P) / p.36 (837I) -- ST01="837", ST02=control number,
    # ST03=implementation reference, must match GS08.
    env.add("ST", "837", st_control_number, _ST03_BY_CLAIM_TYPE[claim_type])
    env.add("BHT", "0019", "00", st_control_number, _fmt_date(submission_date), submission_time, "RP")
    mco = encounters[0].mco
    # SOURCE: p.12-13 (837P) / p.37 (837I) -- Loop 1000A submitter
    # (NM101=41, NM108=46 trading partner id qualifier); Loop 1000B
    # receiver (NM101=40, fixed DHS identity).
    env.add("NM1", "41", "2", mco.name, "", "", "", "", "46", mco.trading_partner_id)
    env.add("PER", "IC", f"{mco.name} EDI Contact", "TE", "6515551234")
    env.add("NM1", "40", "2", DHS_PAYER_NAME, "", "", "", "", "46", DHS_PAYER_ID)

    hl_id = 1
    for encounter in encounters:
        hl_id = write_encounter_claim(env, encounter, hl_id=hl_id)

    segment_count = len(env.segments) + 1  # +1 for the SE segment itself
    env.add("SE", str(segment_count), st_control_number)
    return env.segments


def write_batch(
    encounters: Sequence[Encounter],
    *,
    separators: Separators = DEFAULT_SEPARATORS,
    isa_control_number: int = 1,
    gs_control_number: int = 1,
    st_control_number: int = 1,
    usage_indicator: str = "T",
    submission_date: _dt.date | None = None,
    submission_time: str = "0800",
) -> str:
    """Build one full ISA..IEA interchange for a batch of encounters.

    Encounters are grouped by claim_type into separate GS/ST groups (837P
    and 837I cannot share one ST -- different implementation references),
    but always share a single ISA, per "PLEASE SEND ONE INTERCHANGE PER
    FILE" (p.35).
    """
    if not encounters:
        raise ValueError("write_batch requires at least one encounter.")
    submission_date = submission_date or _dt.date.today()
    mco = encounters[0].mco

    isa_cn = f"{isa_control_number:09d}"
    env = EnvelopeBuilder(separators)
    # SOURCE: p.35 -- full ISA element-by-element mapping.
    sender_id = mco.trading_partner_id.ljust(10)[:10] + " " * 5  # NPI/UMPI + 5 trailing spaces
    env.add(
        "ISA",
        "00",
        " " * 10,
        "00",
        " " * 10,
        "ZZ",
        sender_id,
        "30",
        DHS_RECEIVER_FEIN_HYPHENATED + " " * 5,
        submission_date.strftime("%y%m%d"),
        _dt.datetime.now().strftime("%H%M"),
        separators.repetition_separator,
        "00501",
        isa_cn,
        "0",
        usage_indicator,
        separators.sub_element_separator,
    )

    by_type: dict[str, list[Encounter]] = {}
    for e in encounters:
        by_type.setdefault(e.claim_type, []).append(e)

    gs_cn = gs_control_number
    st_cn = st_control_number
    for claim_type, group in by_type.items():
        gs_control_str = str(gs_cn)
        env.add(
            "GS",
            "HC",
            mco.trading_partner_id,
            DHS_RECEIVER_FEIN_HYPHENATED,
            submission_date.strftime("%Y%m%d"),
            submission_time,
            gs_control_str,
            "X",
            _GS08_BY_CLAIM_TYPE[claim_type],
        )
        st_segments = write_transaction_set(
            group,
            separators=separators,
            st_control_number=str(st_cn),
            submission_date=submission_date,
            submission_time=submission_time,
        )
        env.segments.extend(st_segments)
        env.add("GE", "1", gs_control_str)
        gs_cn += 1
        st_cn += 1

    group_count = len(by_type)
    iea_control = isa_cn
    if any(e.scenario_name == ERR_BAD_ENVELOPE_SCENARIO for e in encounters):
        # Deliberately mismatch IEA02 against ISA13 -- see
        # generator/scenarios/errors.py err_bad_envelope.
        iea_control = f"{(isa_control_number + 999):09d}"
    env.add("IEA", str(group_count), iea_control)
    return env.text()


def write_batch_checked(
    encounters: Sequence[Encounter],
    *,
    allow_inconsistent: bool = False,
    **kwargs,
) -> str:
    """The CLI/generator-facing entry point. Refuses to write any encounter
    that fails generator/consistency.py's checks unless the caller
    explicitly passes allow_inconsistent=True -- this is what satisfies
    "The generator must refuse to write an internally inconsistent
    encounter and must produce a descriptive error identifying the
    problem." `err_*` scenarios are the one sanctioned exception (see
    generator/consistency.py module docstring); the CLI sets
    allow_inconsistent=True automatically when -- and only when -- every
    requested scenario name starts with "err_".
    """
    if not allow_inconsistent:
        err_names = [e.scenario_name for e in encounters if (e.scenario_name or "").startswith("err_")]
        if err_names:
            listed = ", ".join(err_names)
            raise InconsistentEncounterError(
                f"Refusing to write err_* scenario(s) ({listed}) without allow_inconsistent=True. "
                "These fixtures intentionally violate validation rules."
            )
        for encounter in encounters:
            issues = find_inconsistencies(encounter)
            if issues:
                bullets = "\n".join(f"  - {i}" for i in issues)
                raise InconsistentEncounterError(
                    f"Refusing to write encounter {encounter.encounter_id} "
                    f"(scenario={encounter.scenario_name!r}): internally inconsistent:\n{bullets}\n"
                    "Pass allow_inconsistent=True only for deliberate err_* fixtures."
                )
    return write_batch(encounters, **kwargs)
