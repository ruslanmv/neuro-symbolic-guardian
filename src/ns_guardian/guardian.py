from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from z3 import Int, Solver, sat

Operation = Literal["consume", "add"]


@dataclass(frozen=True)
class VerificationResult:
    """Result of a symbolic verification."""

    ok: bool
    message: str
    counter_example: str | None = None


class LogicGuardian:
    """System 2 verification layer using the Z3 SMT solver."""

    def __init__(self) -> None:
        # Base solver with global invariants.
        self._solver = Solver()

        # World-state variables (Z3 symbols)
        self._inventory = Int("inventory")
        self._amount = Int("amount")

        # Fundamental invariants ("laws of physics")
        self._solver.add(self._inventory >= 0)
        self._solver.add(self._amount >= 0)

    def verify_transaction(
        self,
        current_state: int,
        action_value: int,
        operation: Operation,
    ) -> VerificationResult:
        """Verify if applying an operation is logically/physically possible."""

        if operation not in ("consume", "add"):
            return VerificationResult(
                ok=False,
                message=f"Unsupported operation: {operation!r}",
                counter_example="operation_not_supported",
            )
        if current_state < 0:
            return VerificationResult(
                ok=False,
                message="Current state is invalid: inventory cannot be negative.",
                counter_example=f"inventory={current_state}",
            )
        if action_value < 0:
            return VerificationResult(
                ok=False,
                message="Action value is invalid: amount cannot be negative.",
                counter_example=f"amount={action_value}",
            )

        self._solver.push()
        try:
            self._solver.add(self._inventory == int(current_state))
            self._solver.add(self._amount == int(action_value))

            if operation == "consume":
                self._solver.add((self._inventory - self._amount) >= 0)
            else:  # add
                self._solver.add((self._inventory + self._amount) >= 0)

            result = self._solver.check()
            if result == sat:
                return VerificationResult(
                    ok=True,
                    message="✅ Logic Check Passed: Action is physically possible.",
                )

            return VerificationResult(
                ok=False,
                message=(
                    f"⛔ Logic Check Failed: {operation} {action_value} from "
                    f"{current_state} violates constraints (would go negative)."
                ),
                counter_example=f"{operation}({action_value}) on inventory={current_state}",
            )
        finally:
            self._solver.pop()
