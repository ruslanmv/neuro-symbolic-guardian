from __future__ import annotations

import hashlib
import re
import time
import uuid
from typing import Any, Dict, Optional

from .policy import Policy, default_policy_path, load_policy
from .rules.base import RuleSpec
from .rules.inventory import InventoryNonNegativeRule
from .rules.registry import RuleRegistry
from .schemas import AegisDecision, Decision, Intent, RuleHit, Telemetry


_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


class AegisEngine:
    """Core verification engine.

    Takes a validated Intent and returns the standard AegisDecision.
    """

    def __init__(self, policy: Optional[Policy] = None) -> None:
        self.policy = policy or load_policy(default_policy_path())
        self.registry = RuleRegistry()
        # Register built-in rules
        self.registry.register(InventoryNonNegativeRule())

    def verify(self, intent: Intent) -> AegisDecision:
        t0 = time.perf_counter()
        stages: Dict[str, int] = {}
        request_id = str(uuid.uuid4())

        # Stage 1: input scanning (very small baseline)
        s0 = time.perf_counter()
        secret_hit = self._scan_secrets(intent.text)
        stages["input_scan"] = int((time.perf_counter() - s0) * 1000)

        if secret_hit:
            return AegisDecision(
                decision=Decision.deny,
                reason_codes=["input.secret_detected"],
                human_message="Potential secret/API key detected in input; refusing to proceed.",
                policy_version=self.policy.version,
                rule_hits=[
                    RuleHit(
                        rule_id="input.secret_scan",
                        ok=False,
                        code="input.secret_detected",
                        message="Potential secret detected.",
                        details={"pattern": secret_hit},
                    )
                ],
                telemetry=self._telemetry(t0, stages),
                request_id=request_id,
            )

        # Stage 2: rule evaluation
        s1 = time.perf_counter()
        hits: list[RuleHit] = []
        failed: list[RuleHit] = []
        for rule_cfg in self.policy.rules:
            spec = RuleSpec.from_dict(rule_cfg)
            if not spec.enabled:
                continue
            if not self.registry.has(spec.id):
                hits.append(
                    RuleHit(
                        rule_id=spec.id,
                        ok=False,
                        code="policy.unknown_rule",
                        message=f"Policy references unknown rule '{spec.id}'.",
                        details={},
                    )
                )
                failed.append(hits[-1])
                continue
            rule = self.registry.get(spec.id)
            hit = rule.evaluate(intent, spec.params)
            hits.append(hit)
            if not hit.ok:
                failed.append(hit)
        stages["rules"] = int((time.perf_counter() - s1) * 1000)

        if not failed:
            return AegisDecision(
                decision=Decision.allow,
                reason_codes=[],
                human_message="Allowed: all enabled policy checks passed.",
                policy_version=self.policy.version,
                rule_hits=hits,
                telemetry=self._telemetry(t0, stages),
                request_id=request_id,
            )

        # Decide deny vs revise based on risk class
        risk = (intent.action.risk_class or "standard").lower()
        hard_block = risk in {"high", "critical"} or any(h.code.endswith("solver_unknown") for h in failed)
        decision = Decision.deny if hard_block else Decision.revise
        reason_codes = [h.code for h in failed]
        human = "Denied: policy checks failed." if decision == Decision.deny else "Needs revision: policy checks failed."

        return AegisDecision(
            decision=decision,
            reason_codes=reason_codes,
            human_message=human,
            policy_version=self.policy.version,
            rule_hits=hits,
            telemetry=self._telemetry(t0, stages),
            request_id=request_id,
        )

    @staticmethod
    def _scan_secrets(text: str) -> Optional[str]:
        for pat in _SECRET_PATTERNS:
            if pat.search(text or ""):
                return pat.pattern
        return None

    @staticmethod
    def _telemetry(start: float, stages: Dict[str, int]) -> Telemetry:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return Telemetry(latency_ms=latency_ms, stages_ms=stages)

    @staticmethod
    def request_fingerprint(intent: Intent) -> str:
        """Stable hash useful for auditing without storing raw text."""
        blob = f"{intent.text}|{intent.action.op}|{sorted(intent.action.args.items())}".encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
