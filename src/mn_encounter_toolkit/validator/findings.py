"""The validator's output model: a single `Finding` type shared by all four
layers, and text/JSON rendering for the CLI.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    layer: int  # 1, 2, 3, or 4
    rule_id: str
    message: str
    segment_id: str | None = None
    line_number: int | None = None
    source_citation: str | None = None  # populated for Layer 3 findings


def render_text(findings: list[Finding], *, filename: str = "") -> str:
    if not findings:
        return f"{filename}: PASS (0 findings)\n" if filename else "PASS (0 findings)\n"
    lines = []
    header = f"{filename}: {len(findings)} finding(s)" if filename else f"{len(findings)} finding(s)"
    lines.append(header)
    for f in sorted(findings, key=lambda x: (x.line_number or 0, x.layer, x.rule_id)):
        loc = f"line {f.line_number}" if f.line_number is not None else "no line"
        seg = f" [{f.segment_id}]" if f.segment_id else ""
        lines.append(f"  [{f.severity.upper():7}] L{f.layer} {f.rule_id} ({loc}){seg}: {f.message}")
        if f.source_citation:
            lines.append(f"            SOURCE: {f.source_citation}")
    return "\n".join(lines) + "\n"


def render_json(findings: list[Finding], *, filename: str = "") -> str:
    payload = {
        "file": filename,
        "finding_count": len(findings),
        "error_count": sum(1 for f in findings if f.severity == "error"),
        "warning_count": sum(1 for f in findings if f.severity == "warning"),
        "findings": [asdict(f) for f in findings],
    }
    return json.dumps(payload, indent=2)


def exit_code_for(findings: list[Finding]) -> int:
    """CI convention: 0 = clean, 1 = at least one error-level finding. The
    caller is responsible for mapping crashes to exit code 2."""
    return 1 if any(f.severity == "error" for f in findings) else 0
