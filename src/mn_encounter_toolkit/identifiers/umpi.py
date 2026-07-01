"""Synthetic UMPI (Universal Minnesota Provider Identifier) generation.

# TODO: AMBIGUOUS IN SOURCE -- dhs_837_encounter_companion_guide.pdf does not
# state an explicit UMPI character length/format anywhere it is referenced
# (Loop 2010AA/2310A/2310B/2310C/2310D REF*G2, p.13-22 and p.37-44); it only
# says the value is "the DHS UMPI number" carried in REF02. Assumed behavior
# below: 8-character numeric, matching the only DHS-assigned-ID length
# explicitly documented in this guide (the 8-digit member Medicaid ID,
# p.15/p.39). Flagged in KNOWN_LIMITATIONS.md -- revisit if a future
# document (e.g. MHCP provider enrollment manual) gives an explicit UMPI
# format spec.
"""

from __future__ import annotations

import random


def generate_umpi(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(8))
