from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Interface for calling an LLM to produce JSON."""

    @abstractmethod
    def chat_json(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        raise NotImplementedError
