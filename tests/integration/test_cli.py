"""CLI-level integration tests -- calling main() in-process (no subprocess)
so failures show a normal Python traceback, while still exercising the
exact argparse wiring and exit codes a real shell invocation would hit."""

from __future__ import annotations

from pathlib import Path

from mn_encounter_toolkit.cli.main import main


def test_cli_generate_then_validate_clean_batch(tmp_path: Path, capsys):
    out_file = tmp_path / "batch.x12"
    rc = main(
        [
            "generate",
            "--scenario", "clean_professional_original",
            "--scenario", "clean_institutional_original",
            "--seed", "1",
            "--out", str(out_file),
        ]
    )
    assert rc == 0
    assert out_file.exists()

    rc = main(["validate", "--in", str(out_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASS" in out


def test_cli_generate_with_count_multiplies_scenario(tmp_path: Path):
    out_file = tmp_path / "batch.x12"
    rc = main(
        [
            "generate",
            "--scenario", "clean_professional_original",
            "--count", "3",
            "--seed", "2",
            "--out", str(out_file),
        ]
    )
    assert rc == 0
    text = out_file.read_text(encoding="utf-8")
    assert text.count("CLM*") == 3


def test_cli_validate_error_batch_returns_exit_code_1(tmp_path: Path, capsys):
    out_file = tmp_path / "errs.x12"
    rc = main(
        [
            "generate",
            "--scenario", "err_charge_mismatch",
            "--seed", "3",
            "--out", str(out_file),
        ]
    )
    assert rc == 0  # all-err_* batch auto-allows inconsistency

    rc = main(["validate", "--in", str(out_file), "--format", "json"])
    assert rc == 1
    out = capsys.readouterr().out
    assert '"error_count"' in out


def test_cli_validate_layer_subset(tmp_path: Path, capsys):
    out_file = tmp_path / "batch.x12"
    main(["generate", "--scenario", "clean_professional_original", "--seed", "4", "--out", str(out_file)])
    rc = main(["validate", "--in", str(out_file), "--layers", "1,2"])
    assert rc == 0


def test_cli_validate_unknown_layer_returns_exit_code_2(tmp_path: Path):
    out_file = tmp_path / "batch.x12"
    main(["generate", "--scenario", "clean_professional_original", "--seed", "5", "--out", str(out_file)])
    rc = main(["validate", "--in", str(out_file), "--layers", "99"])
    assert rc == 2


def test_cli_generate_refuses_inconsistent_non_error_scenario_without_flag(tmp_path: Path, monkeypatch):
    """Mixing a real (non-err_*) scenario alongside a manually-broken one
    would require allow_inconsistent -- here we simulate that boundary by
    asking the CLI to write a clean scenario but tampering isn't directly
    exposed at the CLI layer, so instead we confirm the auto-detection
    logic: a batch of ONLY err_* scenarios is auto-allowed, but mixing in
    a non-err_* scenario name turns auto-allow off (and the clean
    scenario itself is consistent, so the write still succeeds)."""
    out_file = tmp_path / "mixed.x12"
    rc = main(
        [
            "generate",
            "--scenario", "clean_professional_original",
            "--scenario", "err_charge_mismatch",
            "--seed", "6",
            "--out", str(out_file),
        ]
    )
    # The err_* encounter is genuinely inconsistent and allow_inconsistent
    # was NOT auto-enabled (mixed batch) nor explicitly passed -> refused.
    assert rc == 2


def test_cli_gen999_and_gen835e_roundtrip(tmp_path: Path):
    batch_file = tmp_path / "batch.x12"
    main(["generate", "--scenario", "clean_professional_original", "--seed", "7", "--out", str(batch_file)])

    file_999 = tmp_path / "ack999.x12"
    rc = main(["gen999", "--in", str(batch_file), "--out", str(file_999)])
    assert rc == 0
    assert "ST*999*" in file_999.read_text(encoding="utf-8")

    file_835e = tmp_path / "remit835e.x12"
    rc = main(["gen835e", "--in", str(batch_file), "--out", str(file_835e)])
    assert rc == 0
    assert "ST*835*" in file_835e.read_text(encoding="utf-8")


def test_cli_gen999_simulation_mode_is_deterministic_for_same_seed(tmp_path: Path):
    batch_file = tmp_path / "batch.x12"
    main(["generate", "--scenario", "clean_professional_original", "--seed", "8", "--out", str(batch_file)])

    out_a = tmp_path / "a.x12"
    out_b = tmp_path / "b.x12"
    main(["gen999", "--in", str(batch_file), "--out", str(out_a), "--mode", "simulation", "--seed", "42"])
    main(["gen999", "--in", str(batch_file), "--out", str(out_b), "--mode", "simulation", "--seed", "42"])
    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")


def test_cli_list_scenarios_prints_every_registered_scenario(capsys):
    from mn_encounter_toolkit.generator.scenarios import registry

    rc = main(["list-scenarios"])
    assert rc == 0
    out = capsys.readouterr().out
    for info in registry.list_scenarios():
        assert info.name in out
