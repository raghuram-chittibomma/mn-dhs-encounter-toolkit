"""CARC/RARC/CAGC reference pool for the 835E generator.

# TODO: AMBIGUOUS IN SOURCE -- mucg_835.pdf Appendix A ("Requirements and
# instructions for CARC, RARC, and CAGC use", p.15-16) does NOT itself
# enumerate specific CARC/RARC code values. It explicitly delegates code
# maintenance to two external national bodies: "CARC are updated ...
# published by Washington Publishing Company (wpc-edi.com/reference)" and
# "RARC are maintained by ... CMS and updates ... published by Washington
# Publishing Company", with code *combinations* governed by CAQH-CORE
# (Appendix A.1/A.2). None of those external code-list documents were
# retrieved into docs/reference/ for this project.
#
# The pool below uses a small set of well-known, long-stable, publicly
# documented CARC/RARC codes (the kind that appear in essentially every
# 835 implementation guide's own examples) purely for generating plausible
# synthetic remittances -- it is NOT a DHS- or MN-specific code list, and
# should not be treated as authoritative for production use. Logged in
# KNOWN_LIMITATIONS.md.
#
# Additionally: per dhs_encounter_data_landing_rendered.md, the DHS
# encounter-data landing page explicitly states the AUC MUCGs (including
# this 835 guide) do NOT apply to encounter submissions/responses. This
# generator's segment structure is therefore adapted from the AUC 835
# guide's general 835 mechanics and Appendix C's worked CLP/SVC/CAS/AMT
# examples (p.19-25), with NO confirmed DHS-specific "835E" structural
# guide -- see KNOWN_LIMITATIONS.md for the full caveat.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CarcRarcPair:
    group_code: str  # CAS01 / CLP-level CAGC: CO, PR, OA, PI
    carc: str
    carc_description: str
    rarc: str | None
    rarc_description: str | None
    weight: int


CARC_RARC_POOL: tuple[CarcRarcPair, ...] = (
    CarcRarcPair(
        "CO", "45",
        "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement.",
        None, None, 8,
    ),
    CarcRarcPair(
        "CO", "97",
        "The benefit for this service is included in the payment/allowance for another "
        "service/procedure that has already been adjudicated.",
        None, None, 4,
    ),
    CarcRarcPair("PR", "1", "Deductible amount.", None, None, 2),
    CarcRarcPair("PR", "2", "Coinsurance amount.", None, None, 2),
    CarcRarcPair("PR", "3", "Co-payment amount.", None, None, 2),
    CarcRarcPair(
        "CO", "96", "Non-covered charge(s).",
        "N130", "Consult plan benefit documents/guidelines for information about restrictions "
        "for this service.", 5,
    ),
    CarcRarcPair(
        "CO", "197", "Precertification/authorization/notification/pre-treatment absent.",
        "N657", "This should be billed with the appropriate code for the procedure performed.", 2,
    ),
    CarcRarcPair(
        "OA", "23",
        "The impact of prior payer(s) adjudication, including payments and/or adjustments.",
        None, None, 4,
    ),
    CarcRarcPair("CO", "29", "The time limit for filing has expired.", None, None, 1),
    CarcRarcPair(
        "PI", "16", "Claim/service lacks information or has submission/billing error(s).",
        "N822", "Missing procedure modifier(s).", 1,
    ),
    CarcRarcPair(
        "CO", "A1", "Claim/Service denied.", None, None, 1,
    ),
)


def pick_denial_reason(rng) -> CarcRarcPair:
    pool = [p for p in CARC_RARC_POOL if p.group_code in ("CO", "PI")]
    return rng.choices(pool, weights=[p.weight for p in pool], k=1)[0]
