"""999 / 835E generation for web uploads."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from mn_encounter_toolkit.response.gen_835e import generate_835e_deterministic, generate_835e_simulated
from mn_encounter_toolkit.response.gen_999 import generate_999_deterministic, generate_999_simulated
from mn_encounter_toolkit.validator.findings import exit_code_for
from mn_encounter_toolkit.validator.layer1_envelope import LAYER1
from mn_encounter_toolkit.validator.run import validate_text
from mn_encounter_toolkit.web.common import parse_outcome_weights


@dataclass(frozen=True)
class ResponseGenerationResult:
    output_text: str
    mode: str
    response_type: str  # "999" or "835E"
    layer1_clean: bool
    layer1_error_count: int
    error_message: str | None = None


def _layer1_summary(output_text: str) -> tuple[bool, int]:
    findings = validate_text(output_text, layers=(LAYER1,))
    errors = sum(1 for finding in findings if finding.severity == "error")
    return exit_code_for(findings) == 0, errors


def generate_999_from_text(
    source_text: str,
    *,
    mode: str = "deterministic",
    seed: int = 0,
    outcome_weights: str | None = None,
    isa_control_number: int = 1,
    sender_id: str = "411674742",
    submission_date: date | None = None,
    submission_time: str = "0800",
) -> ResponseGenerationResult:
    render_kwargs = dict(
        isa_control_number=isa_control_number,
        receiver_id=sender_id,
        submission_date=submission_date,
        submission_time=submission_time,
    )
    try:
        if mode == "deterministic":
            output = generate_999_deterministic(source_text, **render_kwargs)
        elif mode == "simulation":
            rng = random.Random(seed)
            output = generate_999_simulated(
                source_text,
                rng,
                outcome_weights=parse_outcome_weights(outcome_weights),
                **render_kwargs,
            )
        else:
            raise ValueError(f"Unknown mode {mode!r}; use 'deterministic' or 'simulation'.")
    except Exception as exc:  # noqa: BLE001 -- surface to UI
        return ResponseGenerationResult(
            output_text="",
            mode=mode,
            response_type="999",
            layer1_clean=False,
            layer1_error_count=0,
            error_message=str(exc),
        )
    clean, error_count = _layer1_summary(output)
    return ResponseGenerationResult(
        output_text=output,
        mode=mode,
        response_type="999",
        layer1_clean=clean,
        layer1_error_count=error_count,
    )


def generate_835e_from_text(
    source_text: str,
    *,
    mode: str = "deterministic",
    seed: int = 0,
    outcome_weights: str | None = None,
    isa_control_number: int = 1,
    payment_method: str = "NON",
    submission_date: date | None = None,
    submission_time: str = "0800",
) -> ResponseGenerationResult:
    render_kwargs = dict(
        isa_control_number=isa_control_number,
        payment_method=payment_method,
        submission_date=submission_date,
        submission_time=submission_time,
    )
    try:
        if mode == "deterministic":
            output = generate_835e_deterministic(source_text, **render_kwargs)
        elif mode == "simulation":
            rng = random.Random(seed)
            output = generate_835e_simulated(
                source_text,
                rng,
                outcome_weights=parse_outcome_weights(outcome_weights),
                **render_kwargs,
            )
        else:
            raise ValueError(f"Unknown mode {mode!r}; use 'deterministic' or 'simulation'.")
    except Exception as exc:  # noqa: BLE001
        return ResponseGenerationResult(
            output_text="",
            mode=mode,
            response_type="835E",
            layer1_clean=False,
            layer1_error_count=0,
            error_message=str(exc),
        )
    clean, error_count = _layer1_summary(output)
    return ResponseGenerationResult(
        output_text=output,
        mode=mode,
        response_type="835E",
        layer1_clean=clean,
        layer1_error_count=error_count,
    )
