from __future__ import annotations

import json
import os
from typing import Any

import requests

from .base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible Chat Completions API client.

    Works with OpenAI and any API implementing the /v1/chat/completions endpoint.
    Configure via environment variables:
      - AEGIS_LLM_BASE_URL (default: https://api.openai.com)
      - AEGIS_LLM_API_KEY
      - AEGIS_LLM_MODEL (default: gpt-4o-mini)

    Note: this repo does not bundle an OpenAI SDK to keep dependencies small.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("AEGIS_LLM_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.api_key = api_key or os.getenv("AEGIS_LLM_API_KEY")
        self.model = model or os.getenv("AEGIS_LLM_MODEL") or "gpt-4o-mini"
        if not self.api_key:
            raise ValueError("AEGIS_LLM_API_KEY is required")

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Request JSON output if supported; keep it best-effort to remain compatible.
        response_format: dict[str, Any] = {"type": "json_object"}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": response_format,
        }

        r = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()

        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except Exception as e:
            raise ValueError(f"Model did not return valid JSON: {e}") from e
