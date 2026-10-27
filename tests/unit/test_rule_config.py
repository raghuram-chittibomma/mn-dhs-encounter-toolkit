"""Suppressed validation rules are saved locally and skipped on upload."""

import json
import re
from pathlib import Path

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.web.rule_config import load_suppressed_rule_ids, save_suppressed_rule_ids
from mn_encounter_toolkit.web.validate_service import validate_upload


def test_missing_config_enables_every_rule(tmp_path: Path):
    assert load_suppressed_rule_ids(tmp_path / "missing.json") == frozenset()


def test_round_trip_keeps_known_rule_ids(tmp_path: Path):
    path = tmp_path / "suppressed_rules.json"
    path.write_text(
        json.dumps({"suppressed": ["L2-AMT02-MONEY-FORMAT", "NOT-A-RULE"]}),
        encoding="utf-8",
    )
    loaded = load_suppressed_rule_ids(path)
    assert loaded == frozenset({"L2-AMT02-MONEY-FORMAT"})

    save_suppressed_rule_ids(loaded | {"ALSO-UNKNOWN"}, path)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored == {"suppressed": ["L2-AMT02-MONEY-FORMAT"]}


def test_suppressed_error_is_omitted_and_validation_can_pass():
    encounter = registry.build_encounter("clean_professional_original", seed=1)
    source = write_batch_checked([encounter])
    broken = re.sub(r"(AMT\*[A-Z0-9]+\*)\d+\.\d{2}", r"\g<1>0", source, count=1)
    full = validate_upload(broken, filename="broken.x12")
    assert any(item.finding.rule_id == "L2-AMT02-MONEY-FORMAT" for item in full.findings)
    assert full.exit_code == 1

    error_ids = frozenset(item.finding.rule_id for item in full.findings if item.finding.severity == "error")
    quiet = validate_upload(broken, filename="broken.x12", suppressed_rule_ids=error_ids)
    assert quiet.exit_code == 0
    assert quiet.error_count == 0
    assert all(item.finding.rule_id not in error_ids for item in quiet.findings)
