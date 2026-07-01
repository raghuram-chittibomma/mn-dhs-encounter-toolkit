"""Command-line entry point: ``mn-encounter <subcommand> ...``.

Subcommands:
    generate        Build one or more synthetic encounters and write an
                     837P/837I X12 file.
    validate        Run the four-layer validator against an X12 file.
    gen999          Generate a 999 Implementation Acknowledgment for a
                     previously generated 837 file.
    gen835e         Generate an 835E encounter-remittance file for a
                     previously generated 837 file.
    list-scenarios  Print every registered generator scenario.

Every subcommand is a thin wrapper around the corresponding library
function in generator/, validator/, or response/ -- the CLI itself
contains no business logic, only argument parsing and file I/O, so every
behavior here is independently unit-testable at the library level too.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.consistency import InconsistentEncounterError
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.response.gen_835e import generate_835e_deterministic, generate_835e_simulated
from mn_encounter_toolkit.response.gen_999 import generate_999_deterministic, generate_999_simulated
from mn_encounter_toolkit.validator.findings import exit_code_for, render_json, render_text
from mn_encounter_toolkit.validator.layer1_envelope import LAYER1
from mn_encounter_toolkit.validator.layer2_syntax import LAYER2
from mn_encounter_toolkit.validator.layer3_dhs_rules import LAYER3
from mn_encounter_toolkit.validator.layer4_consistency import LAYER4
from mn_encounter_toolkit.validator.run import validate_text

_LAYERS_BY_NUMBER = {1: LAYER1, 2: LAYER2, 3: LAYER3, 4: LAYER4}


def _parse_weights(spec: str | None) -> dict[str, int] | None:
    """Parses "A=70,E=20,R=10" -> {"A": 70, "E": 20, "R": 10}."""
    if not spec:
        return None
    weights: dict[str, int] = {}
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, _, value = chunk.partition("=")
        weights[key.strip()] = int(value.strip())
    return weights


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write_text(path: str, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def cmd_list_scenarios(args: argparse.Namespace) -> int:
    for info in registry.list_scenarios():
        tag = " [ERROR FIXTURE]" if info.is_error_scenario else ""
        print(f"{info.name}{tag}\n    {info.description}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    names: list[str] = []
    for name in args.scenario:
        names.extend([name] * args.count)

    all_error_scenarios = bool(names) and all(n.startswith("err_") for n in names)
    allow_inconsistent = args.allow_inconsistent or all_error_scenarios

    encounters = []
    try:
        for name in names:
            info = registry.get_scenario(name)
            encounters.append(info.func(rng))
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        text = write_batch_checked(
            encounters,
            allow_inconsistent=allow_inconsistent,
            isa_control_number=args.isa_control_number,
            gs_control_number=args.gs_control_number,
            st_control_number=args.st_control_number,
            usage_indicator=args.usage_indicator,
        )
    except InconsistentEncounterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_text(args.out, text)
    print(f"Wrote {len(encounters)} encounter(s) ({names}) to {args.out}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.input)
    except OSError as exc:
        print(f"error: could not read {args.input}: {exc}", file=sys.stderr)
        return 2

    layer_numbers = [int(n) for n in args.layers.split(",")] if args.layers else [1, 2, 3, 4]
    try:
        layers = tuple(_LAYERS_BY_NUMBER[n] for n in layer_numbers)
    except KeyError as exc:
        print(f"error: unknown layer {exc}; valid layers are 1, 2, 3, 4", file=sys.stderr)
        return 2

    try:
        findings = validate_text(text, layers=layers)
    except Exception as exc:  # noqa: BLE001 -- CLI boundary: never let a parser crash escape uncaught
        print(f"error: validator crashed: {exc}", file=sys.stderr)
        return 2

    rendered = render_json(findings, filename=args.input) if args.format == "json" else render_text(findings, filename=args.input)
    if args.out:
        _write_text(args.out, rendered)
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return exit_code_for(findings)


def cmd_gen999(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.input)
    except OSError as exc:
        print(f"error: could not read {args.input}: {exc}", file=sys.stderr)
        return 2

    render_kwargs = dict(isa_control_number=args.isa_control_number, receiver_id=args.sender_id)
    try:
        if args.mode == "deterministic":
            out = generate_999_deterministic(text, **render_kwargs)
        else:
            rng = random.Random(args.seed)
            out = generate_999_simulated(text, rng, outcome_weights=_parse_weights(args.outcome_weights), **render_kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"error: 999 generation failed: {exc}", file=sys.stderr)
        return 2

    _write_text(args.out, out)
    print(f"Wrote 999 ({args.mode}) to {args.out}")
    return 0


def cmd_gen835e(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.input)
    except OSError as exc:
        print(f"error: could not read {args.input}: {exc}", file=sys.stderr)
        return 2

    render_kwargs = dict(isa_control_number=args.isa_control_number, payment_method=args.payment_method)
    try:
        if args.mode == "deterministic":
            out = generate_835e_deterministic(text, **render_kwargs)
        else:
            rng = random.Random(args.seed)
            out = generate_835e_simulated(text, rng, outcome_weights=_parse_weights(args.outcome_weights), **render_kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"error: 835E generation failed: {exc}", file=sys.stderr)
        return 2

    _write_text(args.out, out)
    print(f"Wrote 835E ({args.mode}) to {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mn-encounter", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-scenarios", help="List every registered generator scenario")
    p_list.set_defaults(func=cmd_list_scenarios)

    p_gen = sub.add_parser("generate", help="Generate a synthetic 837P/837I encounter batch")
    p_gen.add_argument("--scenario", action="append", required=True, help="Scenario name (repeatable)")
    p_gen.add_argument("--count", type=int, default=1, help="Number of instances per --scenario (default 1)")
    p_gen.add_argument("--seed", type=int, required=True, help="RNG seed -- same seed always reproduces the same output")
    p_gen.add_argument("--out", required=True, help="Output file path")
    p_gen.add_argument("--isa-control-number", type=int, default=1)
    p_gen.add_argument("--gs-control-number", type=int, default=1)
    p_gen.add_argument("--st-control-number", type=int, default=1)
    p_gen.add_argument("--usage-indicator", default="T", choices=["T", "P"], help="ISA15: T=test, P=production")
    p_gen.add_argument(
        "--allow-inconsistent",
        action="store_true",
        help="Write even if a (non-err_*) encounter fails a consistency check (normally refused)",
    )
    p_gen.set_defaults(func=cmd_generate)

    p_val = sub.add_parser("validate", help="Run the four-layer validator against an X12 file")
    p_val.add_argument("--in", dest="input", required=True, help="Input X12 file path")
    p_val.add_argument("--out", help="Write the report here instead of stdout")
    p_val.add_argument("--format", choices=["text", "json"], default="text")
    p_val.add_argument("--layers", help="Comma-separated subset of 1,2,3,4 (default: all four)")
    p_val.set_defaults(func=cmd_validate)

    p_999 = sub.add_parser("gen999", help="Generate a 999 Implementation Acknowledgment")
    p_999.add_argument("--in", dest="input", required=True, help="Original 837 file path")
    p_999.add_argument("--out", required=True, help="Output 999 file path")
    p_999.add_argument("--mode", choices=["deterministic", "simulation"], default="deterministic")
    p_999.add_argument("--seed", type=int, default=0, help="RNG seed (simulation mode only)")
    p_999.add_argument("--isa-control-number", type=int, default=1)
    p_999.add_argument("--sender-id", default="411674742", help="999's ISA06/GS02 sender id (default: DHS payer id)")
    p_999.add_argument(
        "--outcome-weights", help='Simulation mode only, e.g. "A=70,E=20,R=10" (A=accept, E=accept w/errors, R=reject)'
    )
    p_999.set_defaults(func=cmd_gen999)

    p_835 = sub.add_parser("gen835e", help="Generate an 835E encounter-remittance file")
    p_835.add_argument("--in", dest="input", required=True, help="Original 837 file path")
    p_835.add_argument("--out", required=True, help="Output 835E file path")
    p_835.add_argument("--mode", choices=["deterministic", "simulation"], default="deterministic")
    p_835.add_argument("--seed", type=int, default=0, help="RNG seed (simulation mode only)")
    p_835.add_argument("--isa-control-number", type=int, default=1)
    p_835.add_argument("--payment-method", default="NON", choices=["NON", "ACH", "CHK", "FWT"])
    p_835.add_argument(
        "--outcome-weights",
        help='Simulation mode only, e.g. "paid_full=55,paid_partial=30,denied=15"',
    )
    p_835.set_defaults(func=cmd_gen835e)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
