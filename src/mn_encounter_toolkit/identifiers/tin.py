"""Synthetic Tax Identification Number (EIN-shaped) generation.

SOURCE: dhs_837_encounter_companion_guide.pdf -- p.14 (837P) / p.38 (837I),
Loop 2010AA REF segment: "REF01=EI (PROVIDERS EMPLOYER IDENTIFICATION
NUMBER) ... REF02 = PROVIDERS EMPLOYERS IDENTIFICATION NUMBER". Format is a
standard 9-digit US EIN; the guide does not impose an MN-specific format
beyond the EI qualifier itself.
"""

from __future__ import annotations

import random

# Real IRS EIN prefixes are assigned per-campus and change over time; using
# a deliberately-fictional, never-issued prefix block keeps generated TINs
# unambiguously synthetic without needing an up-to-date real prefix list.
_FICTIONAL_TIN_PREFIXES = ("90", "91", "92", "93")


def generate_tin(rng: random.Random) -> str:
    prefix = rng.choice(_FICTIONAL_TIN_PREFIXES)
    rest = "".join(str(rng.randint(0, 9)) for _ in range(7))
    return prefix + rest
