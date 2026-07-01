"""Synthetic MCO and third-party-liability payer name pools.

All names below are fictional and not modeled on any specific real MCO or
insurer; only the *kind* of entity (MN MCO vs. commercial/Medicare TPL
payer) is realistic.
"""

from __future__ import annotations

from dataclasses import dataclass

PROGRAM_CODES = ("PMAP", "MinnesotaCare", "MSHO", "MSC+", "SNBC")

FICTIONAL_MCO_NAMES: tuple[str, ...] = (
    "Northstar Community Health Plan",
    "Heartland Prairie Health",
    "Voyager Health Partners of Minnesota",
    "Anishinaabe Trail Health Plan",
    "Mississippi Headwaters Health Alliance",
)


@dataclass(frozen=True)
class TPLPayerRef:
    name: str
    claim_filing_indicator: str  # SBR09
    weight: int


# SBR09 claim filing indicator codes referenced here (CI, MA, MB, WC, AM) are
# standard base X12 005010 codes (not DHS-specific); see X12 837 IG.
TPL_PAYER_POOL: tuple[TPLPayerRef, ...] = (
    TPLPayerRef("Lakeside Commercial Indemnity", "CI", 5),
    TPLPayerRef("Boreal Mutual Insurance", "CI", 4),
    TPLPayerRef("Federal Medicare Part A", "MA", 3),
    TPLPayerRef("Federal Medicare Part B", "MB", 3),
    TPLPayerRef("Northwoods Workers Compensation Fund", "WC", 1),
    TPLPayerRef("Glacier Ridge Auto Mutual", "AM", 1),
)
