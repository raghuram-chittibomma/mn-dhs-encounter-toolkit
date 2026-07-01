"""Shared, transaction-agnostic X12 primitives: separators and segment
construction. Both the writer and the parser depend on this module, and
NOTHING here hardcodes a delimiter -- delimiters are always either passed in
explicitly (writer) or detected from ISA (parser). This is what satisfies
the spec's "separator characters ... must be configurable -- not hardcoded"
requirement.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Separators:
    """The four X12 delimiters. Defaults are the most common real-world
    choices, but every one is overridable.

    SOURCE: dhs_837_encounter_companion_guide.pdf p.35 (ISA11): "REPETITION
    SEPARATOR -- PLEASE SEND DHS '['". DHS's documented preference for the
    repetition separator is unusual (most implementations use '^'), so it
    is captured as this module's default for DHS-targeted output, while
    remaining fully overridable (e.g. for non-DHS-profile test fixtures).
    """

    segment_terminator: str = "~"
    element_separator: str = "*"
    sub_element_separator: str = ":"
    repetition_separator: str = "["

    def __post_init__(self) -> None:
        seps = {
            self.segment_terminator,
            self.element_separator,
            self.sub_element_separator,
            self.repetition_separator,
        }
        if len(seps) != 4:
            raise ValueError("All four separator characters must be distinct.")
        for s in seps:
            if len(s) != 1:
                raise ValueError(
                    "DHS requires single-byte delimiters only (dhs_837_encounter_companion_guide.pdf "
                    "p.35: 'DO NOT SEND SEGMENT DELIMITERS THAT ARE MORE THAN ONE BYTE.')"
                )


DEFAULT_SEPARATORS = Separators()


def build_segment(separators: Separators, *elements: str | tuple[str, ...]) -> str:
    """Join a segment id + elements into one terminated segment string.
    Composite elements are passed as tuples and joined with the
    sub-element separator; plain elements are passed as strings.
    """
    parts: list[str] = []
    for el in elements:
        if isinstance(el, tuple):
            parts.append(separators.sub_element_separator.join(el))
        else:
            parts.append("" if el is None else str(el))
    return separators.element_separator.join(parts) + separators.segment_terminator


def detect_separators(text: str) -> Separators:
    """Detect the four delimiters from the ISA segment at the start of
    `text`, per the spec: "Separator characters ... detected from ISA --
    never hardcoded." The ISA segment has a fixed-width structure: the
    element separator is the character immediately after "ISA"; the
    sub-element (component) separator is ISA16 (byte 105, 0-indexed, in a
    standard 106-byte ISA); the segment terminator is the byte immediately
    after ISA16; the repetition separator is ISA11.
    """
    if not text.startswith("ISA"):
        raise ValueError("Cannot detect separators: input does not start with an ISA segment.")
    element_sep = text[3]
    fields = text.split(element_sep)
    if len(fields) < 17:
        raise ValueError(
            f"Malformed ISA segment: expected at least 16 elements after ISA, got {len(fields) - 1}."
        )
    repetition_sep = fields[11]
    sub_element_sep = fields[16][0]
    segment_terminator = fields[16][1]
    return Separators(
        segment_terminator=segment_terminator,
        element_separator=element_sep,
        sub_element_separator=sub_element_sep,
        repetition_separator=repetition_sep,
    )
