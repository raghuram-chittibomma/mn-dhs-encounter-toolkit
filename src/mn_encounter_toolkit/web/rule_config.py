"""Which validation rules the EDI file page reports.

The file stores rule IDs only. A missing file means every rule is enabled.
"""

from __future__ import annotations

import json
from pathlib import Path

from mn_encounter_toolkit.web.layer_reference import all_rule_ids


def default_config_path() -> Path:
    return Path.home() / ".mn-encounter" / "suppressed_rules.json"


def load_suppressed_rule_ids(path: Path | None = None) -> frozenset[str]:
    """Known rule IDs the user has turned off. Unknown IDs are ignored."""
    config_path = default_config_path() if path is None else path
    if not config_path.is_file():
        return frozenset()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return frozenset()
    raw = payload.get("suppressed", []) if isinstance(payload, dict) else []
    if not isinstance(raw, list):
        return frozenset()
    known = set(all_rule_ids())
    return frozenset(str(item) for item in raw if str(item) in known)


def save_suppressed_rule_ids(rule_ids: set[str] | frozenset[str], path: Path | None = None) -> None:
    config_path = default_config_path() if path is None else path
    known = set(all_rule_ids())
    suppressed = sorted(rule_id for rule_id in rule_ids if rule_id in known)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"suppressed": suppressed}, indent=2) + "\n", encoding="utf-8")


def filter_findings(findings: list, suppressed_rule_ids: frozenset[str]) -> list:
    if not suppressed_rule_ids:
        return findings
    return [finding for finding in findings if finding.rule_id not in suppressed_rule_ids]
