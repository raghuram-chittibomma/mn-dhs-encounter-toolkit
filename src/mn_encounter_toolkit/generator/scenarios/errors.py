"""Deliberate error fixtures for validator testing.

Every scenario in this module intentionally violates exactly one rule and is
named accordingly. They are NOT bugs: `registry.ScenarioInfo.is_error_scenario`
is True for any "err_*" name, and edi/writer.py requires callers to pass
`allow_inconsistent=True` to write one of these -- see generator/
consistency.py's module docstring for the policy this implements.
"""

from __future__ import annotations

import dataclasses
import random
from decimal import Decimal

from mn_encounter_toolkit.generator.entities import generate_icn
from mn_encounter_toolkit.generator.scenarios.clean import clean_institutional_original, clean_professional_original
from mn_encounter_toolkit.generator.scenarios.registry import register_scenario
from mn_encounter_toolkit.generator.scenarios.tpl import professional_with_tpl
from mn_encounter_toolkit.models.encounter import Encounter


@register_scenario("err_missing_umpi", "UMPI required but absent -- MN rule violation")
def err_missing_umpi(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    # Empty string is this toolkit's "absent" sentinel for UMPI (the field
    # is typed as a required str elsewhere); edi/writer.py omits the REF*G2
    # segment entirely when umpi is falsy, producing a file genuinely
    # missing the UMPI reference for Layer 3 to catch.
    broken_billing = dataclasses.replace(base.billing_provider, umpi="")
    # clean_professional_original uses the same provider for billing and
    # rendering; keep them in sync here too so the writer doesn't emit a
    # spurious extra 2310B rendering-provider loop just because the two
    # Provider values now differ only by the umpi field.
    return dataclasses.replace(
        base,
        billing_provider=broken_billing,
        rendering_provider=broken_billing,
        scenario_name="err_missing_umpi",
    )


@register_scenario("err_missing_mco_paid", "MCO-paid amount absent where required")
def err_missing_mco_paid(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    # SOURCE: dhs_837_encounter_companion_guide.pdf Appendix, p.89 -- "837P
    # -- individual paid amounts are at line level." Strip every line's
    # REF*9D-bearing field so the *required* line-level paid amount is
    # genuinely absent from the written file (the 2320 header AMT*D is left
    # alone -- that loop's presence is independently mandatory and is not
    # what this scenario is testing).
    stripped_lines = tuple(
        dataclasses.replace(line, mco_paid_amount_line=None) for line in base.service_lines
    )
    return dataclasses.replace(
        base,
        mco_paid_amount=None,
        service_lines=stripped_lines,
        scenario_name="err_missing_mco_paid",
    )


@register_scenario("err_missing_mco_paid_837i", "837I MCO-paid amount absent (no REF*9D or REF*9C)")
def err_missing_mco_paid_837i(rng: random.Random) -> Encounter:
    base = clean_institutional_original(rng)
    stripped_lines = tuple(
        dataclasses.replace(line, mco_paid_amount_line=None, allowed_amount_line=None)
        for line in base.service_lines
    )
    inst = dataclasses.replace(
        base.institutional,
        mco_paid_amount_claim=None,
        allowed_amount_claim=None,
    )
    return dataclasses.replace(
        base,
        mco_paid_amount=None,
        service_lines=stripped_lines,
        institutional=inst,
        scenario_name="err_missing_mco_paid_837i",
    )


@register_scenario("err_missing_cl1_837i", "837I missing required CL1 institutional claim code segment")
def err_missing_cl1_837i(rng: random.Random) -> Encounter:
    base = clean_institutional_original(rng)
    return dataclasses.replace(base, scenario_name="err_missing_cl1_837i")


@register_scenario("err_missing_statement_dates_837i", "837I missing required DTP*434 statement dates")
def err_missing_statement_dates_837i(rng: random.Random) -> Encounter:
    base = clean_institutional_original(rng)
    return dataclasses.replace(base, scenario_name="err_missing_statement_dates_837i")


@register_scenario("err_void_no_icn", "Void encounter missing original ICN")
def err_void_no_icn(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    return dataclasses.replace(
        base, frequency_code="8", original_icn=None, scenario_name="err_void_no_icn"
    )


@register_scenario("err_replacement_no_icn", "Replacement encounter missing original ICN")
def err_replacement_no_icn(rng: random.Random) -> Encounter:
    base = clean_institutional_original(rng)
    return dataclasses.replace(
        base, frequency_code="7", original_icn=None, scenario_name="err_replacement_no_icn"
    )


@register_scenario("err_charge_mismatch", "CLM02 total != sum of service line charges")
def err_charge_mismatch(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    bumped_total = base.total_charge_amount + Decimal("50.00")
    return dataclasses.replace(base, total_charge_amount=bumped_total, scenario_name="err_charge_mismatch")


@register_scenario("err_invalid_dx_pointer", "Diagnosis pointer references nonexistent HI position")
def err_invalid_dx_pointer(rng: random.Random) -> Encounter:
    base = clean_professional_original(rng)
    bad_pointer = len(base.diagnoses) + 3  # guaranteed out of range
    bad_lines = list(base.service_lines)
    bad_lines[0] = dataclasses.replace(bad_lines[0], diagnosis_pointers=(bad_pointer,))
    return dataclasses.replace(
        base, service_lines=tuple(bad_lines), scenario_name="err_invalid_dx_pointer"
    )


@register_scenario("err_bad_envelope", "ISA/IEA control number mismatch")
def err_bad_envelope(rng: random.Random) -> Encounter:
    # The corruption itself is file-level (ISA13 vs IEA02), not anything
    # representable on a single Encounter. edi/writer.py looks for this
    # scenario_name on any encounter in a batch and deliberately writes a
    # mismatched IEA02 when it sees it. See edi/writer.py: _ERR_BAD_ENVELOPE_SCENARIO.
    base = clean_professional_original(rng)
    return dataclasses.replace(base, scenario_name="err_bad_envelope")


@register_scenario("err_tpl_amounts_unbalanced", "TPL COB amounts inconsistent with claim total")
def err_tpl_amounts_unbalanced(rng: random.Random) -> Encounter:
    base = professional_with_tpl(rng)
    # Push the TPL-reported paid amount comfortably past the claim total --
    # an internally-impossible COB amount.
    blown_up_tpl = dataclasses.replace(base.tpl, paid_amount=base.total_charge_amount + Decimal("500.00"))
    return dataclasses.replace(base, tpl=blown_up_tpl, scenario_name="err_tpl_amounts_unbalanced")
