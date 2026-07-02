"""Structured validation-layer reference for the web UI and documentation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerRule:
    rule_id: str
    description: str
    severity: str = "error"  # error | warning | info | stub
    notes: str = ""


@dataclass(frozen=True)
class LayerInfo:
    number: int
    title: str
    scope: str
    authority: str
    module_path: str
    rules: tuple[LayerRule, ...]


LAYER_INFO: tuple[LayerInfo, ...] = (
    LayerInfo(
        number=1,
        title="Envelope integrity",
        scope="Interchange and functional-group envelope: ISA, GS, ST, SE, GE, IEA.",
        authority="Base X12 envelope mechanics + DHS one-interchange-per-file rule.",
        module_path="validator/layer1_envelope.py",
        rules=(
            LayerRule("L1-ISA-PRESENT", "ISA segment exists"),
            LayerRule("L1-IEA-PRESENT", "IEA segment exists"),
            LayerRule("L1-ONE-ISA-PER-FILE", "Exactly one ISA per file (DHS requirement)"),
            LayerRule("L1-ISA-IEA-CONTROL-MATCH", "ISA13 equals IEA02"),
            LayerRule("L1-ISA13-FORMAT", "ISA13 is nine digits, not all zeros"),
            LayerRule("L1-IEA-GROUP-COUNT", "IEA01 equals actual GS segment count"),
            LayerRule("L1-GS-GE-CONTROL-MATCH", "Each GS06 equals its paired GE02"),
            LayerRule("L1-GE-ST-COUNT", "GE01 equals ST count within the functional group"),
            LayerRule("L1-ST-SE-CONTROL-MATCH", "Each ST02 equals its paired SE02"),
            LayerRule("L1-SE-SEGMENT-COUNT", "SE01 equals segment count from ST through SE inclusive"),
            LayerRule("L1-SEPARATORS-DISTINCT", "Four delimiters are distinct single characters"),
        ),
    ),
    LayerInfo(
        number=2,
        title="Base X12 / TR3 syntax",
        scope="Transaction-set structure, element formats, and CMS NPI validation inside the 837.",
        authority="X12 005010X222A1 / 005010X223A2 — not DHS encounter business rules.",
        module_path="validator/layer2_syntax.py",
        rules=(
            LayerRule("L2-ST01-VALUE", "ST01 equals 837"),
            LayerRule("L2-BHT-PRESENT", "At least one BHT per transaction set"),
            LayerRule("L2-CLM-EXACTLY-ONE-PER-CLAIM", "Exactly one CLM per claim block"),
            LayerRule("L2-CLM02-MONEY-FORMAT", "CLM02 is non-negative decimal with two places"),
            LayerRule("L2-AMT02-MONEY-FORMAT", "AMT02 is non-negative decimal with two places"),
            LayerRule("L2-DTP-DATE8-FORMAT", "DTP with qualifier D8 has valid CCYYMMDD date"),
            LayerRule("L2-NM1-ENTITY-TYPE-QUALIFIER", "NM102 is 1 (person) or 2 (non-person)"),
            LayerRule("L2-HL-LEVEL-CODE-KNOWN", "HL03 is 20 (billing) or 22 (subscriber)"),
            LayerRule("L2-CLAIM-HAS-SERVICE-LINE", "At least one LX per claim"),
            LayerRule("L2-CLAIM-HAS-DIAGNOSIS", "At least one HI per claim"),
            LayerRule("L2-NPI-CHECK-DIGIT-VALID", "NM109 under XX qualifier passes NPI Luhn check"),
            LayerRule("L2-DIAGNOSIS-CODE-NO-DECIMAL", "HI diagnosis codes contain no decimal point"),
        ),
    ),
    LayerInfo(
        number=3,
        title="DHS encounter business rules",
        scope="Minnesota DHS companion-guide requirements for MCO encounter 837P/837I submissions.",
        authority="docs/reference/dhs_837_encounter_companion_guide.pdf — findings include SOURCE citation.",
        module_path="validator/layer3_dhs_rules.py",
        rules=(
            LayerRule("L3-BILLING-TIN-REQUIRED", "Billing provider REF*EI (TIN) in Loop 2010AA"),
            LayerRule("L3-BILLING-UMPI-REQUIRED", "Billing provider REF*G2 (UMPI) in Loop 2010AA"),
            LayerRule("L3-REFERRING-UMPI-REQUIRED", "REF*G2 when NM1*DN referring provider is present"),
            LayerRule("L3-RENDERING-UMPI-REQUIRED", "REF*G2 when NM1*82 rendering provider is present"),
            LayerRule("L3-MCO-ADJUDICATION-REQUIRED", "Loop 2320 first occurrence reports MCO adjudication (AMT*D)"),
            LayerRule("L3-PAYER-NAME-FIXED", "Loop 2010BB payer is MN Dept of Human Services"),
            LayerRule("L3-RECEIVER-FIXED", "Loop 1000B receiver NM1*40 identity"),
            LayerRule("L3-SUBMITTER-TRADING-PARTNER-QUALIFIER", "Loop 1000A submitter NM108 equals 46"),
            LayerRule("L3-SENDER-ID-MATCHES-SUBMITTER", "ISA06 equals GS02 and submitter NM109"),
            LayerRule("L3-ISA-RECEIVER-FIXED", "ISA07=30 and ISA08/GS03 match DHS receiver FEIN"),
            LayerRule("L3-MEMBER-ID-EIGHT-DIGITS", "Subscriber NM109 is eight-digit DHS member id"),
            LayerRule("L3-EPSDT-NU-WHEN-NO-REFERRAL", "CRC03 is NU when CRC02 is N (no referral)"),
            LayerRule("L3-VOID-REF-F8-ONLY", "REF*F8 appears only on void claims (CLM05-3=8)"),
            LayerRule("L3-DIAGNOSIS-PRINCIPAL-QUALIFIER", "First HI uses ABK principal qualifier"),
            LayerRule("L3-DIAGNOSIS-SUBSEQUENT-QUALIFIER", "Subsequent HI segments use ABF"),
            LayerRule("L3-LINE-PAID-AMOUNT-REQUIRED-837P", "At least one line-level REF*9D on 837P claims"),
            LayerRule(
                "L3-LINE-PAID-AMOUNT-REQUIRED-837I",
                "837I: REF*9D on a service line or REF*9C at claim level (loop 2300)",
            ),
            LayerRule(
                "L3-837I-AMOUNT-REF-PLACEMENT",
                "837I: 9A/9C only in loop 2300; 9B/9D only at service-line level",
            ),
            LayerRule("L3-LINE-PAID-AMOUNT-NOT-NEGATIVE", "Line paid/allowed amounts are not negative"),
            LayerRule(
                "L3-CLM05-3-FREQUENCY-CODE-DOCUMENTED",
                "Replacement frequency CLM05-3=7 is documented as a known guide/spec tension",
                severity="warning",
            ),
            LayerRule(
                "L3-UMPI-FORMAT-STUB",
                "Placeholder rule — produces no findings (UMPI format unconfirmed in source docs)",
                severity="stub",
                notes="See KNOWN_LIMITATIONS.md",
            ),
        ),
    ),
    LayerInfo(
        number=4,
        title="Cross-field consistency",
        scope="Relationships between segments and amounts on the same parsed claim.",
        authority="Toolkit internal consistency checks (not an external PDF citation).",
        module_path="validator/layer4_consistency.py",
        rules=(
            LayerRule("L4-CHARGE-BALANCE", "CLM02 equals sum of service line charge amounts"),
            LayerRule("L4-DX-POINTER-RANGE", "Diagnosis pointers reference existing HI positions"),
            LayerRule("L4-MCO-PAID-NOT-EXCEED-CHARGE", "First 2320 AMT*D does not exceed CLM02"),
            LayerRule("L4-VOID-REPLACEMENT-HAS-ICN", "Void/replacement claims carry original ICN reference"),
            LayerRule("L4-TPL-AMOUNTS-BALANCE", "TPL 2320 amounts do not exceed CLM02 when TPL is present"),
            LayerRule("L4-INSTITUTIONAL-DATE-ORDER", "837I admission date is on or before discharge date"),
        ),
    ),
)

LAYER_BY_NUMBER: dict[int, LayerInfo] = {layer.number: layer for layer in LAYER_INFO}

VALIDATION_LAYERS_DOC = "docs/VALIDATION_LAYERS.md"

# Backward-compatible summaries for sidebar snippets.
LAYER_SUMMARIES: dict[int, dict[str, str]] = {
    layer.number: {
        "title": layer.title,
        "scope": layer.scope,
        "rules": ", ".join(rule.rule_id for rule in layer.rules),
    }
    for layer in LAYER_INFO
}


def all_rule_ids() -> list[str]:
    return [rule.rule_id for layer in LAYER_INFO for rule in layer.rules]


def find_rules(query: str) -> list[tuple[LayerInfo, LayerRule]]:
    needle = query.strip().lower()
    if not needle:
        return []
    matches: list[tuple[LayerInfo, LayerRule]] = []
    for layer in LAYER_INFO:
        for rule in layer.rules:
            haystack = f"{rule.rule_id} {rule.description} {rule.notes}".lower()
            if needle in haystack:
                matches.append((layer, rule))
    return matches
