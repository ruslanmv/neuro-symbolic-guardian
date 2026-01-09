from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import Intent


class IntentExtractor(ABC):
    """Extract an Intent from free text."""

    @abstractmethod
    def extract(self, text: str, *, facts=None) -> Intent:
        raise NotImplementedError
