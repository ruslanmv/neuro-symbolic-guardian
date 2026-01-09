from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMProvider(ABC):
    """Interface for calling an LLM to produce JSON."""

    @abstractmethod
    def chat_json(
        self,
        system: str,
        user: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        timeout_s: float = 15.0,
    ) -> Dict[str, Any]:
        raise NotImplementedError
