from __future__ import annotations

from typing import Any, Dict

from z3 import Int, Solver, sat

from ..schemas import Intent, RuleHit


class InventoryNonNegativeRule:
    """Ensures inventory cannot become negative.

    Expects intent.action.op in {"consume","add"} with args:
      - current_state: int
      - amount: int
    """

    rule_id = "inventory.non_negative"

    def evaluate(self, intent: Intent, params: Dict[str, Any]) -> RuleHit:
        op = intent.action.op
        args = intent.action.args or {}

        if op not in ("consume", "add"):
            return RuleHit(
                rule_id=self.rule_id,
                ok=True,
                code="inventory.op_not_applicable",
                message="Rule not applicable to this operation.",
                details={"op": op},
            )

        try:
            current_state = int(args.get("current_state"))
            amount = int(args.get("amount"))
        except Exception:
            return RuleHit(
                rule_id=self.rule_id,
                ok=False,
                code="inventory.missing_or_invalid_args",
                message="Missing or invalid current_state/amount for inventory operation.",
                details={"args": args},
            )

        if current_state < 0 or amount < 0:
            return RuleHit(
                rule_id=self.rule_id,
                ok=False,
                code="inventory.invalid_input",
                message="Inventory and amount must be non-negative.",
                details={"current_state": current_state, "amount": amount},
            )

        timeout_ms = int(params.get("timeout_ms", 50))
        solver = Solver()
        solver.set(timeout=timeout_ms)

        inventory = Int("inventory")
        amt = Int("amount")

        solver.add(inventory >= 0)
        solver.add(amt >= 0)
        solver.add(inventory == current_state)
        solver.add(amt == amount)

        if op == "consume":
            solver.add(inventory - amt >= 0)
        else:
            solver.add(inventory + amt >= 0)

        result = solver.check()
        if result == sat:
            return RuleHit(
                rule_id=self.rule_id,
                ok=True,
                code="inventory.ok",
                message="Inventory invariant holds.",
                details={"op": op, "current_state": current_state, "amount": amount, "timeout_ms": timeout_ms},
            )

        # Unknown can happen on timeout; treat as fail-closed for high risk
        if str(result) == "unknown":
            return RuleHit(
                rule_id=self.rule_id,
                ok=False,
                code="inventory.solver_unknown",
                message="Solver returned unknown (likely timeout).",
                details={"timeout_ms": timeout_ms},
            )

        return RuleHit(
            rule_id=self.rule_id,
            ok=False,
            code="inventory.would_go_negative",
            message=f"Operation '{op}' would violate non-negative inventory.",
            details={"op": op, "current_state": current_state, "amount": amount},
        )
