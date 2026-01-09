"""
Model catalog for fetching available models from different LLM providers.

Supports:
- OpenAI: Fetches from /v1/models endpoint
- Claude: Fetches from Anthropic API
- Watsonx: Fetches from public foundation model specs
- Ollama: Fetches from local server
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from .llm_settings import LLMProvider, LLMSettings, get_llm_settings

logger = logging.getLogger(__name__)

# Watsonx configuration
WATSONX_BASE_URLS = [
    "https://us-south.ml.cloud.ibm.com",
    "https://eu-de.ml.cloud.ibm.com",
    "https://jp-tok.ml.cloud.ibm.com",
    "https://au-syd.ml.cloud.ibm.com",
]

WATSONX_ENDPOINT = "/ml/v1/foundation_model_specs"
WATSONX_PARAMS = {
    "version": "2024-09-16",
    "filters": "!function_embedding,!lifecycle_withdrawn",
}
TODAY = datetime.today().strftime("%Y-%m-%d")


def _is_deprecated_or_withdrawn(lifecycle: list[dict[str, Any]]) -> bool:
    """Check if a model is deprecated or withdrawn."""
    for entry in lifecycle:
        if entry.get("id") in {"deprecated", "withdrawn"} and entry.get("start_date", "") <= TODAY:
            return True
    return False


def _list_openai_models(settings: LLMSettings) -> tuple[list[str], str | None]:
    """List models from OpenAI API."""
    api_key = settings.openai.api_key
    if not api_key:
        return [], "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."

    base_url = settings.openai.base_url or "https://api.openai.com/v1"
    url = f"{base_url.rstrip('/')}/models"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        models = sorted({m.get("id", "") for m in data if m.get("id")})
        return models, None
    except Exception as e:
        logger.error(f"Error listing OpenAI models: {e}")
        return [], f"Error listing OpenAI models: {str(e)}"


def _list_claude_models(settings: LLMSettings) -> tuple[list[str], str | None]:
    """List models from Anthropic API."""
    api_key = settings.claude.api_key
    if not api_key:
        return [], "Claude (Anthropic) API key not configured. Set ANTHROPIC_API_KEY environment variable."

    base_url = settings.claude.base_url or "https://api.anthropic.com"
    url = f"{base_url.rstrip('/')}/v1/models"

    try:
        response = requests.get(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        models = sorted({m.get("id", "") for m in data if m.get("id")})
        return models, None
    except Exception as e:
        logger.error(f"Error listing Claude models: {e}")
        # Fallback to known models if API call fails
        fallback_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-sonnet-4-5",
        ]
        return fallback_models, f"Using fallback models (API error: {str(e)})"


def _list_watsonx_models(settings: LLMSettings) -> tuple[list[str], str | None]:
    """List models from Watsonx public specs endpoint."""
    all_models = set()

    for base in WATSONX_BASE_URLS:
        url = f"{base}{WATSONX_ENDPOINT}"
        try:
            response = requests.get(url, params=WATSONX_PARAMS, timeout=10)
            response.raise_for_status()
            resources = response.json().get("resources", [])
            for m in resources:
                if _is_deprecated_or_withdrawn(m.get("lifecycle", [])):
                    continue
                model_id = m.get("model_id")
                if model_id:
                    all_models.add(model_id)
        except Exception as e:
            logger.warning(f"Error fetching Watsonx models from {base}: {e}")
            continue

    if not all_models:
        # Fallback to known models
        fallback_models = [
            "ibm/granite-3-8b-instruct",
            "ibm/granite-3-2b-instruct",
            "meta-llama/llama-3-3-70b-instruct",
            "meta-llama/llama-3-1-70b-instruct",
            "mistralai/mistral-large-2",
        ]
        return sorted(fallback_models), "Using fallback models (public specs unavailable)"

    return sorted(all_models), None


def _list_ollama_models(settings: LLMSettings) -> tuple[list[str], str | None]:
    """List models from local Ollama server."""
    base_url = settings.ollama.base_url or "http://localhost:11434"
    url = f"{base_url.rstrip('/')}/api/tags"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json().get("models", [])
        models = sorted({m.get("name", "") for m in data if m.get("name")})
        return models, None
    except Exception as e:
        logger.error(f"Error listing Ollama models from {url}: {e}")
        return [], f"Error connecting to Ollama server at {base_url}. Is Ollama running?"


def list_models_for_provider(
    provider: LLMProvider,
    settings: LLMSettings | None = None,
) -> tuple[list[str], str | None]:
    """List available models for a given provider.

    Args:
        provider: The LLM provider to query
        settings: Optional settings (uses global settings if not provided)

    Returns:
        Tuple of (models list, error message or None)
    """
    if settings is None:
        settings = get_llm_settings()

    if provider == LLMProvider.openai:
        return _list_openai_models(settings)
    elif provider == LLMProvider.claude:
        return _list_claude_models(settings)
    elif provider == LLMProvider.watsonx:
        return _list_watsonx_models(settings)
    elif provider == LLMProvider.ollama:
        return _list_ollama_models(settings)

    return [], f"Unsupported provider: {provider}"


def get_model_info(provider: LLMProvider, model_id: str, settings: LLMSettings | None = None) -> dict[str, Any]:
    """Get detailed information about a specific model.

    Args:
        provider: The LLM provider
        model_id: The model identifier
        settings: Optional settings

    Returns:
        Dictionary with model information
    """
    if settings is None:
        settings = get_llm_settings()

    # This is a simplified version - could be expanded with more API calls
    info: dict[str, Any] = {
        "provider": provider.value,
        "model_id": model_id,
        "available": True,
    }

    # Add provider-specific info
    if provider == LLMProvider.openai:
        info["api_endpoint"] = settings.openai.base_url
    elif provider == LLMProvider.claude:
        info["api_endpoint"] = settings.claude.base_url
    elif provider == LLMProvider.watsonx:
        info["api_endpoint"] = settings.watsonx.base_url
        info["project_id"] = settings.watsonx.project_id
    elif provider == LLMProvider.ollama:
        info["api_endpoint"] = settings.ollama.base_url

    return info
