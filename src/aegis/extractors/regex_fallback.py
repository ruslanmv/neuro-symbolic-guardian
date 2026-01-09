from __future__ import annotations

import re
from typing import Any

from ..schemas import Action, Facts, Intent
from .base import IntentExtractor


class RegexFallbackExtractor(IntentExtractor):
    """Very small non-LLM extractor for demos.

    This is intentionally limited and should be used only as a fallback.
    """

    _consume = re.compile(r"consume\s+(?P<amount>\d+)", re.I)
    _add = re.compile(r"add\s+(?P<amount>\d+)", re.I)
    _from = re.compile(r"from\s+(?P<state>\d+)", re.I)

    def extract(self, text: str, *, facts: dict[str, Any] | None = None) -> Intent:
        txt = text or ""
        amount = None
        op = None

        m = self._consume.search(txt)
        if m:
            op = "consume"
            amount = int(m.group("amount"))
        else:
            m = self._add.search(txt)
            if m:
                op = "add"
                amount = int(m.group("amount"))

        state = 0
        m2 = self._from.search(txt)
        if m2:
            state = int(m2.group("state"))
        elif isinstance(facts, dict):
            state = int(facts.get("inventory", 0))

        if op is None:
            op = "unknown"

        args = {"current_state": state, "amount": amount if amount is not None else 0}
        return Intent(
            text=txt,
            action=Action(op=op, args=args, risk_class="standard"),
            facts=Facts(data=facts or {}),
            assumptions=["Extracted via regex fallback"],
            prompt_version="regex_fallback_v1",
        )
