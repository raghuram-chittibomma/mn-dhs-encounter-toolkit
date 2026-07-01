"""CPT/HCPCS procedure pool (837P), revenue code pool and ICD-10-PCS
procedure pool (837I), covering services common in MN MCO networks.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProcedureRef:
    code: str
    description: str
    category: str
    typical_charge: Decimal  # plausible average billed charge for this code
    weight: int


PROCEDURE_POOL: tuple[ProcedureRef, ...] = (
    # Evaluation & Management
    ProcedureRef("99213", "Office visit, established patient, low complexity", "em", Decimal("125.00"), 9),
    ProcedureRef("99214", "Office visit, established patient, moderate complexity", "em", Decimal("185.00"), 7),
    ProcedureRef("99203", "Office visit, new patient, low complexity", "em", Decimal("160.00"), 5),
    ProcedureRef("99396", "Periodic preventive exam, established patient, 40-64 yrs", "preventive", Decimal("210.00"), 4),
    ProcedureRef("99385", "Initial preventive exam, new patient, 18-39 yrs", "preventive", Decimal("220.00"), 3),
    ProcedureRef("G0438", "Annual wellness visit, first visit", "preventive", Decimal("175.00"), 3),
    # Behavioral health (H-codes / psychotherapy)
    ProcedureRef("H0031", "Mental health assessment, by non-physician", "behavioral_health", Decimal("150.00"), 5),
    ProcedureRef("H0004", "Behavioral health counseling and therapy, per 15 min", "behavioral_health", Decimal("60.00"), 6),
    ProcedureRef("H2011", "Crisis intervention service, per 15 min", "behavioral_health", Decimal("75.00"), 3),
    ProcedureRef("H0038", "Self-help/peer support services, per 15 min", "behavioral_health", Decimal("40.00"), 3),
    ProcedureRef("90834", "Psychotherapy, 45 minutes", "behavioral_health", Decimal("130.00"), 6),
    # LTSS / waiver HCPCS
    ProcedureRef("T1019", "Personal care services, per 15 minutes", "ltss_waiver", Decimal("25.00"), 5),
    ProcedureRef("S5125", "Attendant care services, per 15 minutes", "ltss_waiver", Decimal("28.00"), 3),
    ProcedureRef("T2025", "Waiver services, NOS", "ltss_waiver", Decimal("90.00"), 2),
    ProcedureRef("T2003", "Non-emergency transportation, encounter/trip", "ltss_waiver", Decimal("35.00"), 3),
    # Lab
    ProcedureRef("80053", "Comprehensive metabolic panel", "lab", Decimal("65.00"), 6),
    ProcedureRef("85025", "Complete blood count, automated, w/ differential", "lab", Decimal("40.00"), 6),
    ProcedureRef("81025", "Urine pregnancy test", "lab", Decimal("20.00"), 2),
    # Radiology
    ProcedureRef("71046", "Chest x-ray, 2 views", "radiology", Decimal("110.00"), 3),
    ProcedureRef("70450", "CT head/brain without contrast", "radiology", Decimal("450.00"), 2),
    ProcedureRef("73610", "X-ray ankle, 3+ views", "radiology", Decimal("95.00"), 2),
)

REVENUE_CODE_POOL: tuple[ProcedureRef, ...] = (
    ProcedureRef("0120", "Room & board, semi-private (medical/surgical)", "rev_room_board", Decimal("1450.00"), 6),
    ProcedureRef("0128", "Room & board, semi-private (pediatric)", "rev_room_board", Decimal("1600.00"), 2),
    ProcedureRef("0450", "Emergency room", "rev_er", Decimal("950.00"), 5),
    ProcedureRef("0250", "Pharmacy, general classification", "rev_pharmacy", Decimal("300.00"), 5),
    ProcedureRef("0300", "Laboratory, general classification", "rev_lab", Decimal("220.00"), 4),
    ProcedureRef("0360", "Operating room services", "rev_or", Decimal("3200.00"), 3),
    ProcedureRef("0636", "Drugs requiring detailed coding", "rev_pharmacy", Decimal("480.00"), 3),
    ProcedureRef("0710", "Recovery room", "rev_or", Decimal("600.00"), 2),
    ProcedureRef("0901", "Behavioral health treatment/services", "rev_behavioral_health", Decimal("1100.00"), 3),
)


def _pcs_code(rng_chars: str) -> str:
    """A structurally valid-looking 7-character ICD-10-PCS code.

    PCS codes use the 34-character set 0-9 and A-H, J-N, P-Z (the letters I
    and O are excluded to avoid confusion with 1 and 0). These pool entries
    are illustrative/synthetic, not drawn from a real PCS code table --
    DRG/PCS specificity is informational for this toolkit's synthetic data,
    not validated against a real PCS code list.
    """
    return rng_chars


ICD10_PCS_POOL: tuple[str, ...] = (
    "0DTJ0ZZ",  # informational/synthetic: resection-shaped, GI system
    "0W3R8ZZ",  # informational/synthetic: control-shaped, anatomical region
    "0SRC0ZZ",  # informational/synthetic: replacement-shaped, lower joints
    "5A1955Z",  # informational/synthetic: respiratory assistance-shaped
    "0BJK8ZZ",  # informational/synthetic: inspection-shaped, respiratory
)


def category_pool(category: str) -> tuple[ProcedureRef, ...]:
    return tuple(p for p in PROCEDURE_POOL if p.category == category)
