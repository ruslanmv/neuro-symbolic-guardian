"""
Multi-provider LLM client abstraction.

Provides a unified interface for OpenAI, Claude, Watsonx, and Ollama.
Compatible with CrewAI and standard OpenAI-compatible interfaces.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from .llm_settings import LLMProvider, LLMSettings, get_llm_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client interface."""

    def __init__(self, settings: LLMSettings | None = None) -> None:
        """Initialize LLM client with settings."""
        self.settings = settings or get_llm_settings()
        self.provider = self.settings.provider
        self.config = self.settings.get_active_config()

    def chat_completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send chat completion request and return response text."""
        if self.provider == LLMProvider.openai:
            return self._openai_completion(messages, **kwargs)
        elif self.provider == LLMProvider.claude:
            return self._claude_completion(messages, **kwargs)
        elif self.provider == LLMProvider.watsonx:
            return self._watsonx_completion(messages, **kwargs)
        elif self.provider == LLMProvider.ollama:
            return self._ollama_completion(messages, **kwargs)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _openai_completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """OpenAI-compatible completion."""
        from .llm_settings import OpenAIConfig

        config = self.config
        assert isinstance(config, OpenAIConfig)

        if not config.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        url = f"{config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise

    def _claude_completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Anthropic Claude completion."""
        from .llm_settings import ClaudeConfig

        config = self.config
        assert isinstance(config, ClaudeConfig)

        if not config.api_key:
            raise ValueError("Claude API key is required. Set ANTHROPIC_API_KEY environment variable.")

        # Set environment variables for CrewAI compatibility
        os.environ["ANTHROPIC_API_KEY"] = config.api_key
        if config.base_url:
            os.environ["ANTHROPIC_BASE_URL"] = config.base_url

        url = f"{config.base_url.rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Convert OpenAI-style messages to Claude format
        system_message = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append(msg)

        payload: dict[str, Any] = {
            "model": config.model,
            "messages": claude_messages,
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
            "temperature": kwargs.get("temperature", config.temperature),
        }

        if system_message:
            payload["system"] = system_message

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
        except Exception as e:
            logger.error(f"Claude completion failed: {e}")
            raise

    def _watsonx_completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """IBM Watsonx completion."""
        from .llm_settings import WatsonxConfig

        config = self.config
        assert isinstance(config, WatsonxConfig)

        if not config.api_key or not config.project_id:
            raise ValueError(
                "Watsonx API key and project ID are required. "
                "Set WATSONX_API_KEY and WATSONX_PROJECT_ID environment variables."
            )

        # Set environment variables for watsonx SDK
        os.environ["WATSONX_API_KEY"] = config.api_key
        os.environ["WATSONX_PROJECT_ID"] = config.project_id
        os.environ["WATSONX_URL"] = config.base_url

        # Convert messages to single prompt
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        url = f"{config.base_url.rstrip('/')}/ml/v1/text/generation?version=2024-09-16"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model_id": config.model_id,
            "input": prompt,
            "parameters": {
                "temperature": kwargs.get("temperature", config.temperature),
                "max_new_tokens": kwargs.get("max_tokens", config.max_tokens),
            },
            "project_id": config.project_id,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["results"][0]["generated_text"]
        except Exception as e:
            logger.error(f"Watsonx completion failed: {e}")
            raise

    def _ollama_completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Ollama local completion."""
        from .llm_settings import OllamaConfig

        config = self.config
        assert isinstance(config, OllamaConfig)

        url = f"{config.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", config.temperature),
                "num_predict": kwargs.get("max_tokens", config.max_tokens),
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise


def build_llm_client(settings: LLMSettings | None = None) -> LLMClient:
    """Build and return an LLM client."""
    return LLMClient(settings)


def build_crewai_llm(settings: LLMSettings | None = None) -> Any:
    """Build a CrewAI-compatible LLM instance.

    This function builds an LLM object compatible with CrewAI's interface.
    """
    try:
        from crewai import LLM
    except ImportError as e:
        raise ImportError("CrewAI is not installed. Install it with: pip install crewai") from e

    settings = settings or get_llm_settings()
    provider = settings.provider

    if provider == LLMProvider.openai:
        config = settings.openai
        if not config.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        model = config.model
        if not model.startswith("openai/"):
            model = f"openai/{model}"

        return LLM(
            model=model,
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == LLMProvider.claude:
        config = settings.claude
        if not config.api_key:
            raise ValueError("Claude API key is required. Set ANTHROPIC_API_KEY environment variable.")

        # Set as environment variable (CrewAI requirement)
        os.environ["ANTHROPIC_API_KEY"] = config.api_key
        if config.base_url:
            os.environ["ANTHROPIC_BASE_URL"] = config.base_url

        model = config.model
        if not model.startswith("anthropic/"):
            model = f"anthropic/{model}"

        return LLM(
            model=model,
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == LLMProvider.watsonx:
        config = settings.watsonx
        if not config.api_key or not config.project_id:
            raise ValueError(
                "Watsonx API key and project ID are required. "
                "Set WATSONX_API_KEY and WATSONX_PROJECT_ID environment variables."
            )

        # Set environment variables
        os.environ["WATSONX_API_KEY"] = config.api_key
        os.environ["WATSONX_PROJECT_ID"] = config.project_id
        os.environ["WATSONX_URL"] = config.base_url

        model = config.model_id
        if not model.startswith("watsonx/"):
            model = f"watsonx/{model}"

        return LLM(
            model=model,
            api_key=config.api_key,
            base_url=config.base_url,
            project_id=config.project_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == LLMProvider.ollama:
        config = settings.ollama

        model = config.model
        if not model.startswith("ollama/"):
            model = f"ollama/{model}"

        return LLM(
            model=model,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    raise ValueError(f"Unsupported provider: {provider}")
