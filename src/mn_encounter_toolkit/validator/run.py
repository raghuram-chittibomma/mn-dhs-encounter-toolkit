"""Orchestrates all four validator layers against one X12 file.

Per the architecture: each layer receives the same ParsedDocument and
returns its findings independently -- no layer calls another, and any
layer can be run alone (see tests/unit/test_layer*.py for exactly that).
"""

from __future__ import annotations

from mn_encounter_toolkit.edi.parser import ParsedDocument, parse_segments
from mn_encounter_toolkit.validator.findings import Finding
from mn_encounter_toolkit.validator.layer1_envelope import LAYER1
from mn_encounter_toolkit.validator.layer2_syntax import LAYER2
from mn_encounter_toolkit.validator.layer3_dhs_rules import LAYER3
from mn_encounter_toolkit.validator.layer4_consistency import LAYER4

ALL_LAYERS = (LAYER1, LAYER2, LAYER3, LAYER4)


def validate_document(doc: ParsedDocument, *, layers: tuple = ALL_LAYERS) -> list[Finding]:
    findings: list[Finding] = []
    for layer in layers:
        findings.extend(layer.run(doc))
    return findings


def validate_text(text: str, *, layers: tuple = ALL_LAYERS) -> list[Finding]:
    doc = parse_segments(text)
    return validate_document(doc, layers=layers)


def validate_file(path: str, *, layers: tuple = ALL_LAYERS) -> list[Finding]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return validate_text(text, layers=layers)
