from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..providers.base import LLMProvider
from ..schemas import Action, Facts, Intent
from .base import IntentExtractor

SYSTEM_PROMPT = """You are Aegis, an intent extraction component.
Return only JSON with keys: action, assumptions.
The action must include: op (string), args (object), risk_class (string).
Do not include any extra keys.
"""


class LLMIntentExtractor(IntentExtractor):
    """LLM-backed structured extractor with strict validation."""

    def __init__(self, provider: LLMProvider, prompt_version: str = "llm_intent_v1") -> None:
        self.provider = provider
        self.prompt_version = prompt_version

    def extract(self, text: str, *, facts: dict[str, Any] | None = None) -> Intent:
        user_prompt = self._build_user_prompt(text, facts or {})
        raw = self.provider.chat_json(SYSTEM_PROMPT, user_prompt, timeout_s=15.0)

        try:
            action = Action.model_validate(raw.get("action", {}))
        except ValidationError as e:
            raise ValueError(f"Invalid action schema: {e}") from e

        assumptions = raw.get("assumptions", [])
        if not isinstance(assumptions, list):
            assumptions = [str(assumptions)]

        return Intent(
            text=text or "",
            action=action,
            facts=Facts(data=facts or {}),
            assumptions=[str(a) for a in assumptions],
            prompt_version=self.prompt_version,
        )

    @staticmethod
    def _build_user_prompt(text: str, facts: dict[str, Any]) -> str:
        return (
            "Extract a structured action from the user request.\n"
            "User text:\n"
            f"{text}\n\n"
            "Known facts (JSON):\n"
            f"{facts}\n\n"
            "Respond with JSON only."
        )
