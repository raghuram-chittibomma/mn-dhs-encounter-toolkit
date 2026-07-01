"""Shared rule-registry infrastructure for Layers 2, 3, and 4.

Each layer module creates its own `RuleRegistry(layer=N)` and registers
small, independently-testable functions onto it. This is what satisfies
"Every validation rule must be implemented as an individually testable
function/rule object" -- a unit test can call any one rule function
directly with a hand-built ParsedDocument, with no dependency on the other
rules or on the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mn_encounter_toolkit.edi.parser import ParsedDocument
from mn_encounter_toolkit.validator.findings import Finding

RuleFunc = Callable[[ParsedDocument], list[Finding]]


@dataclass(frozen=True)
class RuleInfo:
    rule_id: str
    description: str
    layer: int
    func: RuleFunc
    source_citation: str | None = None


class RuleRegistry:
    def __init__(self, layer: int) -> None:
        self.layer = layer
        self._rules: dict[str, RuleInfo] = {}

    def register(
        self, rule_id: str, description: str, *, source_citation: str | None = None
    ) -> Callable[[RuleFunc], RuleFunc]:
        def decorator(func: RuleFunc) -> RuleFunc:
            if rule_id in self._rules:
                raise ValueError(f"Rule {rule_id!r} already registered in layer {self.layer}.")
            self._rules[rule_id] = RuleInfo(
                rule_id=rule_id,
                description=description,
                layer=self.layer,
                func=func,
                source_citation=source_citation,
            )
            return func

        return decorator

    def rules(self) -> list[RuleInfo]:
        return [self._rules[k] for k in sorted(self._rules)]

    def run(self, doc: ParsedDocument) -> list[Finding]:
        findings: list[Finding] = []
        for rule in self.rules():
            findings.extend(rule.func(doc))
        return findings
