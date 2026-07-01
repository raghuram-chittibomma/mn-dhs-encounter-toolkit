"""X12 text -> structured representation.

Produces a flat, line-numbered list of segments (ParsedSegment) plus
convenience accessors (ParsedDocument) for envelope segments and per-claim
"blocks" grouped by HL hierarchy. This is intentionally not a full,
generic TR3 loop-tree builder -- it is exactly as much structure as the
four validator layers need, kept simple enough to stay auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mn_encounter_toolkit.edi.x12_core import Separators, detect_separators


@dataclass
class ParsedSegment:
    seg_id: str
    elements: list[str | tuple[str, ...]]  # elements AFTER the segment id
    line_number: int
    raw: str

    def el(self, index: int) -> str | tuple[str, ...] | None:
        """1-based element index (el(1) is the first element after the
        segment id, matching X12's own SEGID01/02/... numbering)."""
        i = index - 1
        if 0 <= i < len(self.elements):
            return self.elements[i]
        return None

    def el_str(self, index: int) -> str:
        v = self.el(index)
        if v is None:
            return ""
        if isinstance(v, tuple):
            return v[0] if v else ""
        return v

    def composite(self, index: int) -> tuple[str, ...]:
        v = self.el(index)
        if v is None:
            return ()
        return v if isinstance(v, tuple) else (v,)


def split_segment(seg_text: str, separators: Separators) -> list[str | tuple[str, ...]]:
    raw_elements = seg_text.split(separators.element_separator)
    parsed: list[str | tuple[str, ...]] = []
    for raw in raw_elements:
        if separators.sub_element_separator in raw:
            parsed.append(tuple(raw.split(separators.sub_element_separator)))
        else:
            parsed.append(raw)
    return parsed


@dataclass
class ClaimBlock:
    """All segments belonging to one claim: the billing-provider (2000A/
    2010AA) segments that head it, and the subscriber-through-service-line
    (2000B onward) segments. `hl_billing_id`/`hl_subscriber_id` are the raw
    HL01 values, useful for Layer 1 hierarchy checks.
    """

    hl_billing_id: str
    hl_subscriber_id: str
    hl_subscriber_parent_id: str
    billing_segments: list[ParsedSegment]
    claim_segments: list[ParsedSegment]

    def find(self, seg_id: str) -> list[ParsedSegment]:
        return [s for s in self.claim_segments if s.seg_id == seg_id]

    def find_in_billing(self, seg_id: str) -> list[ParsedSegment]:
        return [s for s in self.billing_segments if s.seg_id == seg_id]

    def first(self, seg_id: str) -> ParsedSegment | None:
        found = self.find(seg_id)
        return found[0] if found else None

    def clm(self) -> ParsedSegment | None:
        return self.first("CLM")


@dataclass
class ParsedDocument:
    segments: list[ParsedSegment]
    separators: Separators
    source_text: str

    def find(self, seg_id: str) -> list[ParsedSegment]:
        return [s for s in self.segments if s.seg_id == seg_id]

    def first(self, seg_id: str) -> ParsedSegment | None:
        found = self.find(seg_id)
        return found[0] if found else None

    def segments_in_range(self, start: int, end: int) -> list[ParsedSegment]:
        return self.segments[start:end]

    def claim_blocks(self) -> list[ClaimBlock]:
        """Group segments by HL hierarchy: each "billing" HL (HL03=20) is
        immediately followed (in this toolkit's writer's output) by exactly
        one "subscriber" HL (HL03=22) and that subscriber's full claim --
        see edi/writer.py write_encounter_claim. Segments are sliced
        between consecutive HL segments.
        """
        # HL01=id, HL02=parent id, HL03=level code, HL04=child code.
        hl_indices = [i for i, s in enumerate(self.segments) if s.seg_id == "HL"]
        blocks: list[ClaimBlock] = []
        i = 0
        while i < len(hl_indices):
            idx = hl_indices[i]
            hl = self.segments[idx]
            if hl.el_str(3) != "20":
                i += 1
                continue
            billing_id = hl.el_str(1)
            billing_end = hl_indices[i + 1] if i + 1 < len(hl_indices) else len(self.segments)
            billing_segments = self.segments[idx + 1 : billing_end]

            if i + 1 >= len(hl_indices):
                i += 1
                continue
            sub_idx = hl_indices[i + 1]
            sub_hl = self.segments[sub_idx]
            if sub_hl.el_str(3) != "22":
                i += 1
                continue
            subscriber_id = sub_hl.el_str(1)
            subscriber_parent_id = sub_hl.el_str(2)
            claim_end = hl_indices[i + 2] if i + 2 < len(hl_indices) else len(self.segments)
            claim_segments = self.segments[sub_idx + 1 : claim_end]
            blocks.append(
                ClaimBlock(
                    hl_billing_id=billing_id,
                    hl_subscriber_id=subscriber_id,
                    hl_subscriber_parent_id=subscriber_parent_id,
                    billing_segments=billing_segments,
                    claim_segments=claim_segments,
                )
            )
            i += 2
        return blocks


def parse_segments(text: str, separators: Separators | None = None) -> ParsedDocument:
    if separators is None:
        separators = detect_separators(text)

    segments: list[ParsedSegment] = []
    current_line = 1
    buf: list[str] = []
    i = 0
    n = len(text)
    term = separators.segment_terminator
    while i < n:
        ch = text[i]
        if ch == term:
            seg_text = "".join(buf).strip("\r\n")
            buf = []
            i += 1
            if seg_text.strip():
                elements = split_segment(seg_text, separators)
                seg_id = elements[0] if isinstance(elements[0], str) else elements[0][0]
                segments.append(
                    ParsedSegment(
                        seg_id=seg_id,
                        elements=elements[1:],
                        line_number=current_line,
                        raw=seg_text + term,
                    )
                )
            # Consume any newline(s) immediately following the terminator;
            # they belong "between" this segment and the next.
            while i < n and text[i] in "\r\n":
                if text[i] == "\n":
                    current_line += 1
                i += 1
        else:
            buf.append(ch)
            i += 1

    leftover = "".join(buf).strip()
    if leftover:
        raise ValueError(
            f"Trailing content after the last segment terminator was not empty: {leftover!r}. "
            "The file may be missing a final segment terminator."
        )

    return ParsedDocument(segments=segments, separators=separators, source_text=text)
