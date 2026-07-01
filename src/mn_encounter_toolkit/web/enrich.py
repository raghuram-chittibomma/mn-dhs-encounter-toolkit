"""Map validator findings to claim-level context for the web UI."""

from __future__ import annotations

import re
from dataclasses import dataclass

from mn_encounter_toolkit.edi.parser import ClaimBlock, ParsedDocument
from mn_encounter_toolkit.validator.findings import Finding

_HL_SUBSCRIBER_RE = re.compile(r"subscriber HL (\S+)")
_CLAIM_ID_RE = re.compile(r"\bclaim ([A-Z0-9]+)", re.IGNORECASE)
_CONTEXT_RADIUS = 2


@dataclass(frozen=True)
class ClaimSummary:
    claim_index: int
    claim_id: str | None
    claim_type: str
    subscriber_hl_id: str
    billing_hl_id: str
    member_id: str | None
    member_name: str | None


@dataclass(frozen=True)
class EnrichedFinding:
    finding: Finding
    scope: str  # "file" or "claim"
    claim_index: int | None
    claim_id: str | None
    subscriber_hl_id: str | None
    billing_hl_id: str | None
    member_id: str | None
    member_name: str | None
    claim_type: str | None
    segment_snippet: str | None
    context_lines: tuple[str, ...]
    billing_loop_note: str | None


def _claim_type(block: ClaimBlock) -> str:
    return "837I" if block.find("SV2") else "837P"


def _member_from_block(block: ClaimBlock) -> tuple[str | None, str | None]:
    for nm1 in block.find("NM1"):
        if nm1.el_str(1) == "IL" and nm1.el_str(8) == "MI":
            last, first = nm1.el_str(3), nm1.el_str(4)
            name = ", ".join(part for part in (last, first) if part) or None
            return nm1.el_str(9) or None, name
    return None, None


def summarize_claims(doc: ParsedDocument) -> list[ClaimSummary]:
    summaries: list[ClaimSummary] = []
    for index, block in enumerate(doc.claim_blocks(), start=1):
        clm = block.clm()
        member_id, member_name = _member_from_block(block)
        summaries.append(
            ClaimSummary(
                claim_index=index,
                claim_id=clm.el_str(1) if clm else None,
                claim_type=_claim_type(block),
                subscriber_hl_id=block.hl_subscriber_id,
                billing_hl_id=block.hl_billing_id,
                member_id=member_id,
                member_name=member_name,
            )
        )
    return summaries


def _block_line_span(block: ClaimBlock) -> tuple[int, int] | None:
    lines = [segment.line_number for segment in block.billing_segments + block.claim_segments]
    if not lines:
        return None
    return min(lines), max(lines)


def _block_for_line(blocks: list[ClaimBlock], line_number: int) -> tuple[int, ClaimBlock] | None:
    for index, block in enumerate(blocks, start=1):
        span = _block_line_span(block)
        if span and span[0] <= line_number <= span[1]:
            return index, block
    return None


def _block_for_subscriber_hl(blocks: list[ClaimBlock], hl_id: str) -> tuple[int, ClaimBlock] | None:
    for index, block in enumerate(blocks, start=1):
        if block.hl_subscriber_id == hl_id:
            return index, block
    return None


def _block_for_claim_id(blocks: list[ClaimBlock], claim_id: str) -> tuple[int, ClaimBlock] | None:
    for index, block in enumerate(blocks, start=1):
        clm = block.clm()
        if clm and clm.el_str(1) == claim_id:
            return index, block
    return None


def _resolve_claim_block(
    finding: Finding, blocks: list[ClaimBlock]
) -> tuple[int, ClaimBlock] | None:
    if finding.line_number is not None:
        match = _block_for_line(blocks, finding.line_number)
        if match:
            return match

    hl_match = _HL_SUBSCRIBER_RE.search(finding.message)
    if hl_match:
        match = _block_for_subscriber_hl(blocks, hl_match.group(1))
        if match:
            return match

    claim_match = _CLAIM_ID_RE.search(finding.message)
    if claim_match:
        match = _block_for_claim_id(blocks, claim_match.group(1))
        if match:
            return match

    return None


def _lines_by_number(doc: ParsedDocument) -> dict[int, str]:
    return {segment.line_number: segment.raw.rstrip("\r\n") for segment in doc.segments}


def _context_at_line(doc: ParsedDocument, line_number: int | None) -> tuple[str | None, tuple[str, ...]]:
    if line_number is None:
        return None, ()
    by_line = _lines_by_number(doc)
    snippet = by_line.get(line_number)
    if snippet is None:
        return None, ()
    nearby = [
        by_line[num]
        for num in range(line_number - _CONTEXT_RADIUS, line_number + _CONTEXT_RADIUS + 1)
        if num in by_line
    ]
    return snippet, tuple(nearby)


def _billing_loop_note(block: ClaimBlock, finding: Finding) -> str | None:
    if finding.segment_id != "REF" or finding.line_number is not None:
        return None
    refs = block.find_in_billing("REF")
    if refs:
        return "Billing loop REF segments:\n" + "\n".join(segment.raw.rstrip("\r\n") for segment in refs)
    return "Billing loop has no REF segments (Loop 2010AA)."


def enrich_findings(doc: ParsedDocument, findings: list[Finding]) -> list[EnrichedFinding]:
    blocks = doc.claim_blocks()
    summaries = {summary.subscriber_hl_id: summary for summary in summarize_claims(doc)}
    enriched: list[EnrichedFinding] = []

    for finding in findings:
        snippet, context = _context_at_line(doc, finding.line_number)
        match = _resolve_claim_block(finding, blocks)
        if match is None:
            enriched.append(
                EnrichedFinding(
                    finding=finding,
                    scope="file",
                    claim_index=None,
                    claim_id=None,
                    subscriber_hl_id=None,
                    billing_hl_id=None,
                    member_id=None,
                    member_name=None,
                    claim_type=None,
                    segment_snippet=snippet,
                    context_lines=context,
                    billing_loop_note=None,
                )
            )
            continue

        claim_index, block = match
        summary = summaries[block.hl_subscriber_id]
        enriched.append(
            EnrichedFinding(
                finding=finding,
                scope="claim",
                claim_index=claim_index,
                claim_id=summary.claim_id,
                subscriber_hl_id=summary.subscriber_hl_id,
                billing_hl_id=summary.billing_hl_id,
                member_id=summary.member_id,
                member_name=summary.member_name,
                claim_type=summary.claim_type,
                segment_snippet=snippet,
                context_lines=context,
                billing_loop_note=_billing_loop_note(block, finding),
            )
        )
    return enriched
