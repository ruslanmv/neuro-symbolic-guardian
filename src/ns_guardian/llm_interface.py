from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Operation = Literal["consume", "add"]


@dataclass(frozen=True)
class UserIntent:
    """Structured intent extracted from a natural-language request."""

    current_state: int
    action_value: int
    operation: Operation
    original_thought: str


class LLMInterface:
    """Mocked LLM interface.

    In a real integration, this would call IBM Watsonx / OpenAI / Anthropic to:
    1) parse user text into a structured plan (JSON)
    2) optionally emit symbolic constraints

    Phase I prototype keeps this deterministic and testable.
    """

    _HAVE_RE = re.compile(r"\b(?:i\s*have|have)\s*(?P<have>\d+)\b", re.IGNORECASE)
    _EAT_RE = re.compile(
        r"\b(?:eat|consume|use|spend)\s*(?P<eat>\d+)\b", re.IGNORECASE
    )
    _ADD_RE = re.compile(r"\b(?:add|buy|receive|get)\s*(?P<add>\d+)\b", re.IGNORECASE)

    def parse_user_intent(self, user_text: str) -> UserIntent | None:
        """Extract intent from user text.

        Examples:
            "I have 2 apples. I want to eat 3." -> consume 3 from 2
            "I have 2 apples. I want to add 5." -> add 5 to 2
        """

        have_m = self._HAVE_RE.search(user_text)
        if not have_m:
            return None
        current_state = int(have_m.group("have"))

        eat_m = self._EAT_RE.search(user_text)
        add_m = self._ADD_RE.search(user_text)

        if eat_m and add_m:
            # Ambiguous: both consume and add in the same sentence
            return None

        if eat_m:
            action_value = int(eat_m.group("eat"))
            operation: Operation = "consume"
            thought = (
                f"User wants to consume {action_value} from current state {current_state}."
            )
            return UserIntent(current_state, action_value, operation, thought)

        if add_m:
            action_value = int(add_m.group("add"))
            operation = "add"
            thought = f"User wants to add {action_value} to current state {current_state}."
            return UserIntent(current_state, action_value, operation, thought)

        return None

    def generate_response(self, valid: bool, message: str, intent: UserIntent) -> str:
        """Generate final user-facing output (mocked)."""

        if valid:
            if intent.operation == "consume":
                remaining = intent.current_state - intent.action_value
                return (
                    f"🤖 AI Response: Sure! You consume {intent.action_value}. "
                    f"You now have {remaining} left."
                )
            remaining = intent.current_state + intent.action_value
            return (
                f"🤖 AI Response: Done! You add {intent.action_value}. "
                f"You now have {remaining} total."
            )

        return (
            "🛡️ GUARDIAN INTERVENTION: I cannot allow this response.\n"
            f"Reason: {message}"
        )
