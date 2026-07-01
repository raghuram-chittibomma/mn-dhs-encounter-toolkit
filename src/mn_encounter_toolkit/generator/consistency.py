"""Pre-write internal-consistency checks for synthetic Encounters.

Per the spec: "The generator must refuse to write an internally inconsistent
encounter and must produce a descriptive error identifying the problem."
The `err_*` named scenarios are a deliberate, signposted exception to this:
they exist specifically to produce a bad fixture for the validator's test
suite, and must opt in explicitly via `allow_inconsistent=True` wherever
they are written (see edi/writer.py and generator/scenarios/errors.py). Any
*other* scenario that fails these checks is a generation bug, not a fixture,
and must hard-fail.
"""

from __future__ import annotations

from mn_encounter_toolkit.models.encounter import Encounter


class InconsistentEncounterError(ValueError):
    """Raised when an Encounter fails an internal-consistency check and the
    caller has not explicitly opted into writing it anyway."""


def find_inconsistencies(encounter: Encounter) -> list[str]:
    """Return a list of human-readable consistency problems (empty if none).

    These mirror (a strict subset of) the validator's Layer 4 cross-field
    checks, applied pre-write rather than post-parse.
    """
    issues: list[str] = []

    line_total = sum((line.charge_amount for line in encounter.service_lines), start=type(encounter.total_charge_amount)("0"))
    if line_total != encounter.total_charge_amount:
        issues.append(
            f"CLM02 total charge {encounter.total_charge_amount} does not equal the sum of "
            f"service line charge amounts {line_total}"
        )

    if encounter.mco_paid_amount is not None and encounter.mco_paid_amount > encounter.total_charge_amount:
        issues.append(
            f"MCO-paid amount {encounter.mco_paid_amount} exceeds total charge amount "
            f"{encounter.total_charge_amount}"
        )

    valid_positions = set(range(1, len(encounter.diagnoses) + 1))
    for line in encounter.service_lines:
        for pointer in line.diagnosis_pointers:
            if pointer not in valid_positions:
                issues.append(
                    f"service line {line.line_number} diagnosis pointer {pointer} does not "
                    f"reference an existing HI position (claim has {len(encounter.diagnoses)} "
                    "diagnoses)"
                )

    if encounter.frequency_code in ("7", "8") and not encounter.original_icn:
        issues.append(
            f"frequency_code={encounter.frequency_code!r} (replacement/void) requires original_icn"
        )

    if encounter.tpl is not None:
        tpl_total = (
            encounter.tpl.paid_amount
            + encounter.tpl.remaining_patient_liability
            + encounter.tpl.non_covered_amount
        )
        if tpl_total > encounter.total_charge_amount:
            issues.append(
                f"TPL amounts (paid {encounter.tpl.paid_amount} + remaining liability "
                f"{encounter.tpl.remaining_patient_liability} + non-covered "
                f"{encounter.tpl.non_covered_amount} = {tpl_total}) exceed total charge "
                f"{encounter.total_charge_amount}"
            )

    if encounter.institutional is not None:
        if not (
            encounter.institutional.statement_from
            <= encounter.institutional.admission_date
            <= encounter.institutional.discharge_date
            <= encounter.institutional.statement_through
        ):
            issues.append(
                "institutional statement period must satisfy statement_from <= admission_date "
                "<= discharge_date <= statement_through"
            )

    return issues


def ensure_consistent(encounter: Encounter, *, context: str = "") -> None:
    issues = find_inconsistencies(encounter)
    if issues:
        bullet_list = "\n".join(f"  - {issue}" for issue in issues)
        ctx = f" ({context})" if context else ""
        raise InconsistentEncounterError(
            f"Encounter {encounter.encounter_id}{ctx} is internally inconsistent:\n{bullet_list}"
        )
