"""Shared pytest fixtures/helpers for the toolkit's test suite."""

from __future__ import annotations

import random

import pytest

from mn_encounter_toolkit.edi.parser import ParsedDocument, parse_segments
from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.edi.x12_core import DEFAULT_SEPARATORS
from mn_encounter_toolkit.generator.scenarios import registry


def make_doc(*segment_lines: str) -> ParsedDocument:
    """Build a ParsedDocument directly from raw, already-terminated segment
    strings (each WITHOUT its trailing '~') -- a convenience for layer-rule
    unit tests that want a minimal, hand-built document fragment (often
    without an ISA header) rather than a full generated encounter. Uses the
    default separator set explicitly since separator *auto-detection*
    (tested separately in test_writer_parser.py) requires a real ISA
    segment, which most of these minimal fixtures intentionally omit."""
    text = "\n".join(s + "~" for s in segment_lines) + "\n"
    return parse_segments(text, separators=DEFAULT_SEPARATORS)


def encounter_for(scenario_name: str, seed: int = 1):
    return registry.build_encounter(scenario_name, seed)


def write_one(scenario_name: str, seed: int = 1, **kwargs) -> str:
    encounter = registry.build_encounter(scenario_name, seed)
    allow = scenario_name.startswith("err_")
    return write_batch_checked([encounter], allow_inconsistent=allow, **kwargs)


@pytest.fixture
def rng() -> random.Random:
    return random.Random(12345)


@pytest.fixture
def clean_837p_text() -> str:
    return write_one("clean_professional_original", seed=1)


@pytest.fixture
def clean_837i_text() -> str:
    return write_one("clean_institutional_original", seed=1)
