from __future__ import annotations

from typing import Dict

from .base import Rule


class RuleRegistry:
    """In-process rule registry."""

    def __init__(self) -> None:
        self._rules: Dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Rule:
        if rule_id not in self._rules:
            raise KeyError(f"Unknown rule: {rule_id}")
        return self._rules[rule_id]

    def has(self, rule_id: str) -> bool:
        return rule_id in self._rules

    def all(self) -> Dict[str, Rule]:
        return dict(self._rules)
