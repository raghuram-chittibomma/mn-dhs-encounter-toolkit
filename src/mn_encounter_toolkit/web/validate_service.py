"""Validation orchestration for file uploads (web UI and future APIs)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass

from mn_encounter_toolkit.edi.parser import parse_segments
from mn_encounter_toolkit.validator.findings import exit_code_for, render_json
from mn_encounter_toolkit.validator.layer1_envelope import LAYER1
from mn_encounter_toolkit.validator.layer2_syntax import LAYER2
from mn_encounter_toolkit.validator.layer3_dhs_rules import LAYER3
from mn_encounter_toolkit.validator.layer4_consistency import LAYER4
from mn_encounter_toolkit.validator.run import validate_document
from mn_encounter_toolkit.web.enrich import ClaimSummary, EnrichedFinding, enrich_findings, summarize_claims

ALL_LAYER_NUMBERS = (1, 2, 3, 4)
_LAYERS_BY_NUMBER = {1: LAYER1, 2: LAYER2, 3: LAYER3, 4: LAYER4}


@dataclass(frozen=True)
class ValidationReport:
    filename: str
    claims: tuple[ClaimSummary, ...]
    findings: tuple[EnrichedFinding, ...]
    parse_error: str | None
    exit_code: int

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.findings if item.finding.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.findings if item.finding.severity == "warning")

    @property
    def passed(self) -> bool:
        return self.parse_error is None and self.error_count == 0


def layers_from_numbers(layer_numbers: tuple[int, ...]) -> tuple:
    if not layer_numbers:
        raise ValueError("At least one validation layer is required.")
    return tuple(_LAYERS_BY_NUMBER[number] for number in layer_numbers)


def validate_upload(
    text: str,
    *,
    filename: str = "upload.x12",
    layer_numbers: tuple[int, ...] = ALL_LAYER_NUMBERS,
) -> ValidationReport:
    try:
        document = parse_segments(text)
    except ValueError as exc:
        return ValidationReport(
            filename=filename,
            claims=(),
            findings=(),
            parse_error=str(exc),
            exit_code=2,
        )

    layers = layers_from_numbers(layer_numbers)
    raw_findings = validate_document(document, layers=layers)
    claims = tuple(summarize_claims(document))
    enriched = tuple(enrich_findings(document, raw_findings))
    return ValidationReport(
        filename=filename,
        claims=claims,
        findings=enriched,
        parse_error=None,
        exit_code=exit_code_for(raw_findings),
    )


def report_to_json(report: ValidationReport) -> str:
    if report.parse_error:
        return json.dumps(
            {"file": report.filename, "parse_error": report.parse_error, "exit_code": report.exit_code},
            indent=2,
        )
    payload = json.loads(render_json([item.finding for item in report.findings], filename=report.filename))
    payload["claims"] = [
        {
            "claim_index": claim.claim_index,
            "claim_id": claim.claim_id,
            "claim_type": claim.claim_type,
            "subscriber_hl_id": claim.subscriber_hl_id,
            "billing_hl_id": claim.billing_hl_id,
            "member_id": claim.member_id,
            "member_name": claim.member_name,
        }
        for claim in report.claims
    ]
    payload["enriched_findings"] = [
        {
            "severity": item.finding.severity,
            "layer": item.finding.layer,
            "rule_id": item.finding.rule_id,
            "message": item.finding.message,
            "segment_id": item.finding.segment_id,
            "line_number": item.finding.line_number,
            "source_citation": item.finding.source_citation,
            "scope": item.scope,
            "claim_index": item.claim_index,
            "claim_id": item.claim_id,
            "subscriber_hl_id": item.subscriber_hl_id,
            "billing_hl_id": item.billing_hl_id,
            "member_id": item.member_id,
            "member_name": item.member_name,
            "claim_type": item.claim_type,
            "segment_snippet": item.segment_snippet,
            "context_lines": list(item.context_lines),
            "billing_loop_note": item.billing_loop_note,
        }
        for item in report.findings
    ]
    payload["exit_code"] = report.exit_code
    return json.dumps(payload, indent=2)


def report_to_csv(report: ValidationReport) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "severity",
            "layer",
            "rule_id",
            "scope",
            "claim_index",
            "claim_id",
            "claim_type",
            "subscriber_hl_id",
            "member_id",
            "member_name",
            "line_number",
            "segment_id",
            "message",
            "source_citation",
        ]
    )
    for item in report.findings:
        writer.writerow(
            [
                item.finding.severity,
                item.finding.layer,
                item.finding.rule_id,
                item.scope,
                item.claim_index or "",
                item.claim_id or "",
                item.claim_type or "",
                item.subscriber_hl_id or "",
                item.member_id or "",
                item.member_name or "",
                item.finding.line_number or "",
                item.finding.segment_id or "",
                item.finding.message,
                item.finding.source_citation or "",
            ]
        )
    return buffer.getvalue()
