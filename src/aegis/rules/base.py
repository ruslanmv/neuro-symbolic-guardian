from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from ..schemas import Intent, RuleHit


class Rule(Protocol):
    rule_id: str

    def evaluate(self, intent: Intent, params: Dict[str, Any]) -> RuleHit:
        ...


@dataclass
class RuleSpec:
    id: str
    enabled: bool = True
    params: Dict[str, Any] = None  # type: ignore

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RuleSpec":
        return RuleSpec(
            id=str(d.get("id")),
            enabled=bool(d.get("enabled", True)),
            params=dict(d.get("params", {}) or {}),
        )
