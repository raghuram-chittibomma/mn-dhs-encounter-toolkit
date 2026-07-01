"""ICD-10-CM reference pool, weighted toward conditions common in Minnesota
Medicaid / MCO populations.

Codes are stored without decimal points, matching DHS's explicit instruction:
"DO NOT SEND DECIMAL POINTS IN THE DIAGNOSIS CODE" (dhs_837_encounter_
companion_guide.pdf, p.20/p.45, HI segment).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DxRef:
    code: str
    description: str
    category: str
    weight: int  # relative sampling weight


DIAGNOSIS_POOL: tuple[DxRef, ...] = (
    # Behavioral health
    DxRef("F319", "Bipolar disorder, unspecified", "behavioral_health", 6),
    DxRef("F320", "Major depressive disorder, single episode, mild", "behavioral_health", 8),
    DxRef("F332", "Major depressive disorder, recurrent severe w/o psychotic features", "behavioral_health", 5),
    DxRef("F4310", "Post-traumatic stress disorder, unspecified", "behavioral_health", 5),
    DxRef("F900", "ADHD, predominantly inattentive type", "behavioral_health", 6),
    DxRef("F841", "Atypical autism", "behavioral_health", 3),
    DxRef("F411", "Generalized anxiety disorder", "behavioral_health", 7),
    DxRef("F250", "Schizoaffective disorder, bipolar type", "behavioral_health", 3),
    # Substance use
    DxRef("F1120", "Opioid dependence, uncomplicated", "substance_use", 6),
    DxRef("F1010", "Alcohol abuse, uncomplicated", "substance_use", 5),
    DxRef("F1220", "Cannabis dependence, uncomplicated", "substance_use", 4),
    DxRef("F1421", "Cocaine dependence with intoxication, uncomplicated", "substance_use", 2),
    # Chronic conditions
    DxRef("E1165", "Type 2 diabetes mellitus with hyperglycemia", "chronic", 7),
    DxRef("I10", "Essential (primary) hypertension", "chronic", 9),
    DxRef("J449", "Chronic obstructive pulmonary disease, unspecified", "chronic", 5),
    DxRef("N183", "Chronic kidney disease, stage 3", "chronic", 3),
    DxRef("E785", "Hyperlipidemia, unspecified", "chronic", 6),
    DxRef("J45909", "Unspecified asthma, uncomplicated", "chronic", 5),
    # Maternal / child health
    DxRef("Z3480", "Encounter for supervision of other normal pregnancy", "maternal_child", 4),
    DxRef("O09213", "Supervision of pregnancy with history of pre-term labor, 2nd trimester", "maternal_child", 2),
    DxRef("Z00121", "Encounter for routine child health exam with abnormal findings", "maternal_child", 4),
    DxRef("P0721", "Extreme immaturity of newborn, 24 completed weeks of gestation", "maternal_child", 1),
    # Developmental disabilities
    DxRef("F70", "Mild intellectual disabilities", "developmental_disability", 3),
    DxRef("F840", "Autistic disorder", "developmental_disability", 4),
    DxRef("Q909", "Down syndrome, unspecified", "developmental_disability", 2),
    DxRef("F803", "Mixed receptive-expressive language disorder", "developmental_disability", 3),
    # Injuries
    DxRef("S0290XA", "Unspecified fracture of skull, initial encounter", "injury", 1),
    DxRef("S72001A", "Fracture of unspecified part of neck of right femur, initial", "injury", 2),
    DxRef("S93401A", "Sprain of unspecified ligament of right ankle, initial", "injury", 3),
    DxRef("T07", "Unspecified multiple injuries", "injury", 2),
)


def category_pool(category: str) -> tuple[DxRef, ...]:
    return tuple(dx for dx in DIAGNOSIS_POOL if dx.category == category)
