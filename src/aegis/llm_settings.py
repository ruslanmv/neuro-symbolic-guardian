"""
Multi-provider LLM configuration and settings management.

Supports OpenAI, Anthropic (Claude), IBM Watsonx, and Ollama.
"""

from __future__ import annotations

import contextlib
import enum
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file if it exists
load_dotenv()

# Configuration directory
CONFIG_DIR = Path.home() / ".neuro-symbolic-guardian"
CONFIG_FILE = CONFIG_DIR / "settings.json"


class LLMProvider(str, enum.Enum):
    """Supported LLM providers."""

    openai = "openai"
    claude = "claude"
    watsonx = "watsonx"
    ollama = "ollama"


class OpenAIConfig(BaseModel):
    """OpenAI provider configuration."""

    api_key: str = Field(default="", description="OpenAI API key")
    model: str = Field(default="gpt-4o-mini", description="Model name")
    base_url: str = Field(default="https://api.openai.com/v1", description="Base URL for API")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)


class ClaudeConfig(BaseModel):
    """Anthropic Claude provider configuration."""

    api_key: str = Field(default="", description="Anthropic API key")
    model: str = Field(default="claude-sonnet-4-5", description="Model name")
    base_url: str = Field(default="https://api.anthropic.com", description="Base URL for API")
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=1)


class WatsonxConfig(BaseModel):
    """IBM Watsonx provider configuration."""

    api_key: str = Field(default="", description="Watsonx API key")
    project_id: str = Field(default="", description="Watsonx project ID")
    model_id: str = Field(default="ibm/granite-3-8b-instruct", description="Model ID")
    base_url: str = Field(default="https://us-south.ml.cloud.ibm.com", description="Watsonx base URL")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)


class OllamaConfig(BaseModel):
    """Ollama local provider configuration."""

    base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model: str = Field(default="llama3", description="Model name")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)


class LLMSettings(BaseModel):
    """Comprehensive LLM settings with multi-provider support."""

    # Active provider
    provider: LLMProvider = Field(default=LLMProvider.openai)

    # Provider-specific configurations
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    watsonx: WatsonxConfig = Field(default_factory=WatsonxConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)

    # General settings
    enable_llm_extraction: bool = Field(
        default=False, description="Enable LLM-based intent extraction (requires API key)"
    )
    fallback_to_regex: bool = Field(default=True, description="Fallback to regex if LLM fails")

    @classmethod
    def from_disk(cls) -> LLMSettings:
        """Load settings from disk and merge with environment variables."""
        # Load from disk if exists
        if CONFIG_FILE.exists():
            import json

            data = json.loads(CONFIG_FILE.read_text("utf-8"))
            settings = cls.model_validate(data)
        else:
            settings = cls()

        # Override with environment variables (higher priority)
        env_provider = os.getenv("AEGIS_LLM_PROVIDER") or os.getenv("LLM_PROVIDER")
        if env_provider:
            with contextlib.suppress(ValueError):
                settings.provider = LLMProvider(env_provider.lower())

        # Enable LLM extraction if configured
        if os.getenv("AEGIS_ENABLE_LLM"):
            settings.enable_llm_extraction = os.getenv("AEGIS_ENABLE_LLM", "").lower() in ("1", "true", "yes")

        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            settings.openai.api_key = os.getenv("OPENAI_API_KEY", "")
        if os.getenv("OPENAI_MODEL") or os.getenv("AEGIS_LLM_MODEL"):
            settings.openai.model = os.getenv("OPENAI_MODEL") or os.getenv("AEGIS_LLM_MODEL", "gpt-4o-mini")
        if os.getenv("OPENAI_BASE_URL") or os.getenv("AEGIS_LLM_BASE_URL"):
            settings.openai.base_url = os.getenv("OPENAI_BASE_URL") or os.getenv(
                "AEGIS_LLM_BASE_URL", "https://api.openai.com/v1"
            )

        # Claude
        if os.getenv("ANTHROPIC_API_KEY"):
            settings.claude.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if os.getenv("CLAUDE_MODEL"):
            settings.claude.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
        if os.getenv("ANTHROPIC_BASE_URL"):
            settings.claude.base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

        # Watsonx
        if os.getenv("WATSONX_API_KEY"):
            settings.watsonx.api_key = os.getenv("WATSONX_API_KEY", "")
        if os.getenv("WATSONX_PROJECT_ID"):
            settings.watsonx.project_id = os.getenv("WATSONX_PROJECT_ID", "")
        if os.getenv("WATSONX_MODEL"):
            settings.watsonx.model_id = os.getenv("WATSONX_MODEL", "ibm/granite-3-8b-instruct")
        if os.getenv("WATSONX_BASE_URL") or os.getenv("WATSONX_URL"):
            settings.watsonx.base_url = os.getenv("WATSONX_BASE_URL") or os.getenv(
                "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
            )

        # Ollama
        if os.getenv("OLLAMA_BASE_URL"):
            settings.ollama.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        if os.getenv("OLLAMA_MODEL"):
            settings.ollama.model = os.getenv("OLLAMA_MODEL", "llama3")

        return settings

    def save(self) -> None:
        """Save settings to disk."""
        # Skip on ephemeral filesystems (Vercel, etc.)
        if os.getenv("VERCEL") or os.getenv("AEGIS_EPHEMERAL"):
            import logging

            logging.warning("Settings persistence disabled on ephemeral filesystem. Use environment variables.")
            return

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(self.model_dump_json(indent=2), "utf-8")

    def get_active_config(self) -> OpenAIConfig | ClaudeConfig | WatsonxConfig | OllamaConfig:
        """Get the configuration for the active provider."""
        if self.provider == LLMProvider.openai:
            return self.openai
        elif self.provider == LLMProvider.claude:
            return self.claude
        elif self.provider == LLMProvider.watsonx:
            return self.watsonx
        elif self.provider == LLMProvider.ollama:
            return self.ollama
        raise ValueError(f"Unknown provider: {self.provider}")


# Global settings instance
_settings: LLMSettings | None = None


def get_llm_settings() -> LLMSettings:
    """Get the global LLM settings instance."""
    global _settings
    if _settings is None:
        _settings = LLMSettings.from_disk()
    return _settings


def set_provider(provider: LLMProvider) -> LLMSettings:
    """Set the active LLM provider."""
    settings = get_llm_settings()
    settings.provider = provider
    settings.save()
    return settings


def update_llm_settings(updates: dict[str, Any]) -> LLMSettings:
    """Update LLM settings with partial configuration."""
    settings = get_llm_settings()

    # Update provider if present
    if "provider" in updates:
        settings.provider = LLMProvider(updates["provider"])

    # Update provider-specific configs
    if "openai" in updates:
        settings.openai = OpenAIConfig(**updates["openai"])
    if "claude" in updates:
        settings.claude = ClaudeConfig(**updates["claude"])
    if "watsonx" in updates:
        settings.watsonx = WatsonxConfig(**updates["watsonx"])
    if "ollama" in updates:
        settings.ollama = OllamaConfig(**updates["ollama"])

    # Update general settings
    if "enable_llm_extraction" in updates:
        settings.enable_llm_extraction = bool(updates["enable_llm_extraction"])
    if "fallback_to_regex" in updates:
        settings.fallback_to_regex = bool(updates["fallback_to_regex"])

    settings.save()
    return settings
