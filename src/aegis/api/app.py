from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..config import Settings
from ..engine import AegisEngine
from ..extractors.llm import LLMIntentExtractor
from ..extractors.regex_fallback import RegexFallbackExtractor
from ..llm_providers import LLMClient, build_llm_client
from ..llm_settings import (
    LLMProvider,
    get_llm_settings,
    set_provider,
    update_llm_settings,
)
from ..model_catalog import get_model_info, list_models_for_provider
from ..providers.openai_compat import OpenAICompatibleProvider
from ..schemas import AegisDecision, Intent

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, GeneratorRegistry, Histogram, generate_latest

    _METRICS_ENABLED = True
except Exception:  # pragma: no cover
    _METRICS_ENABLED = False

logger = logging.getLogger(__name__)

# ============================================================================
# Application Initialization
# ============================================================================

app = FastAPI(
    title="Neuro-Symbolic Guardian API",
    version="2.0.0",
    description="Production-ready API for LLM verification with symbolic logic",
)

# CORS Configuration
allowed_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS enabled for origins: {allowed_origins}")

# Legacy settings (for backward compatibility)
settings = Settings.from_env()
engine = AegisEngine(policy=settings.load_policy())
regex_extractor = RegexFallbackExtractor()

# New LLM system
llm_settings = get_llm_settings()
llm_client: LLMClient | None = None

# Legacy LLM extractor
if settings.enable_llm:
    provider = OpenAICompatibleProvider()
    llm_extractor: LLMIntentExtractor | None = LLMIntentExtractor(provider)
else:
    llm_extractor = None

# Prometheus metrics
if _METRICS_ENABLED:
    _reg = GeneratorRegistry()
    REQUESTS = Counter("aegis_requests_total", "Total Aegis requests", ["endpoint", "decision"], registry=_reg)
    LATENCY = Histogram("aegis_latency_ms", "Aegis request latency (ms)", ["endpoint"], registry=_reg)


# ============================================================================
# Request/Response Models
# ============================================================================

class VerifyRequest(BaseModel):
    """Request to verify an action."""

    text: str = Field(..., description="Natural language description of the action")
    facts: dict[str, Any] = Field(default_factory=dict, description="World-state facts")
    intent: Intent | None = Field(None, description="Pre-extracted intent (optional)")


class LLMSettingsResponse(BaseModel):
    """Response for LLM settings."""

    provider: LLMProvider
    providers: list[LLMProvider]
    openai: dict[str, Any]
    claude: dict[str, Any]
    watsonx: dict[str, Any]
    ollama: dict[str, Any]
    enable_llm_extraction: bool
    fallback_to_regex: bool


class ModelListResponse(BaseModel):
    """Response for model listing."""

    provider: LLMProvider
    models: list[str]
    error: str | None = None


class ProviderUpdate(BaseModel):
    """Update provider request."""

    provider: LLMProvider


class ChatRequest(BaseModel):
    """Chat completion request."""

    messages: list[dict[str, str]] = Field(..., description="Chat messages")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1)


class ChatResponse(BaseModel):
    """Chat completion response."""

    content: str
    provider: str
    model: str


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "neuro-symbolic-guardian"}


@app.get("/readyz")
def readyz() -> dict[str, Any]:
    """Readiness check with detailed status."""
    return {
        "status": "ready",
        "policy_version": engine.policy.version,
        "llm_enabled": bool(llm_extractor),
        "active_provider": llm_settings.provider.value,
        "rules_count": len(engine.policy.rules),
    }


@app.get("/api/status")
def api_status() -> dict[str, Any]:
    """Comprehensive API status."""
    return {
        "status": "operational",
        "version": "2.0.0",
        "components": {
            "guardian_engine": "ok",
            "policy_system": "ok",
            "llm_integration": "ok" if llm_settings.enable_llm_extraction else "disabled",
            "metrics": "ok" if _METRICS_ENABLED else "disabled",
        },
        "policy": {
            "version": engine.policy.version,
            "rules_count": len(engine.policy.rules),
            "enabled_rules": len([r for r in engine.policy.rules if r.get("enabled", True)]),
        },
        "llm": {
            "provider": llm_settings.provider.value,
            "extraction_enabled": llm_settings.enable_llm_extraction,
        },
    }


# ============================================================================
# Verification Endpoints (Core Guardian Functionality)
# ============================================================================

@app.post("/api/verify", response_model=AegisDecision)
@app.post("/verify", response_model=AegisDecision)  # Legacy endpoint
def verify_action(request: VerifyRequest) -> AegisDecision:
    """Verify if an action complies with policies.

    This is the core Guardian endpoint that verifies actions using
    symbolic logic and policy enforcement.
    """
    try:
        # Extract or use provided intent
        intent = request.intent or extract_intent_internal(request.text, request.facts)

        # Verify with Guardian engine
        endpoint = "/api/verify"
        if _METRICS_ENABLED:
            with LATENCY.labels(endpoint=endpoint).time():
                decision = engine.verify(intent)
        else:
            decision = engine.verify(intent)

        if _METRICS_ENABLED:
            REQUESTS.labels(endpoint=endpoint, decision=str(decision.decision.value)).inc()

        return decision

    except Exception as e:
        logger.error(f"Verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}") from e


@app.post("/api/extract_intent", response_model=Intent)
@app.post("/extract_intent", response_model=Intent)  # Legacy endpoint
def extract_intent_endpoint(payload: dict[str, Any]) -> Intent:
    """Extract structured intent from natural language."""
    text = str(payload.get("text", ""))
    facts = payload.get("facts", {})
    return extract_intent_internal(text, facts)


def extract_intent_internal(text: str, facts: dict[str, Any]) -> Intent:
    """Internal intent extraction logic."""
    if not isinstance(facts, dict):
        raise HTTPException(status_code=400, detail="facts must be an object")

    if llm_extractor is not None and llm_settings.enable_llm_extraction:
        try:
            return llm_extractor.extract(text, facts=facts)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, falling back to regex")
            if llm_settings.fallback_to_regex:
                return regex_extractor.extract(text, facts=facts)
            raise HTTPException(status_code=500, detail=f"Intent extraction failed: {str(e)}") from e

    return regex_extractor.extract(text, facts=facts)


# ============================================================================
# LLM Settings Endpoints
# ============================================================================

@app.get("/api/llm/settings", response_model=LLMSettingsResponse)
def get_llm_settings_endpoint() -> LLMSettingsResponse:
    """Get current LLM settings."""
    return LLMSettingsResponse(
        provider=llm_settings.provider,
        providers=[LLMProvider.openai, LLMProvider.claude, LLMProvider.watsonx, LLMProvider.ollama],
        openai=llm_settings.openai.model_dump(),
        claude=llm_settings.claude.model_dump(),
        watsonx=llm_settings.watsonx.model_dump(),
        ollama=llm_settings.ollama.model_dump(),
        enable_llm_extraction=llm_settings.enable_llm_extraction,
        fallback_to_regex=llm_settings.fallback_to_regex,
    )


@app.post("/api/llm/provider", response_model=LLMSettingsResponse)
def set_llm_provider(update: ProviderUpdate) -> LLMSettingsResponse:
    """Set the active LLM provider."""
    global llm_settings
    llm_settings = set_provider(update.provider)

    return LLMSettingsResponse(
        provider=llm_settings.provider,
        providers=[LLMProvider.openai, LLMProvider.claude, LLMProvider.watsonx, LLMProvider.ollama],
        openai=llm_settings.openai.model_dump(),
        claude=llm_settings.claude.model_dump(),
        watsonx=llm_settings.watsonx.model_dump(),
        ollama=llm_settings.ollama.model_dump(),
        enable_llm_extraction=llm_settings.enable_llm_extraction,
        fallback_to_regex=llm_settings.fallback_to_regex,
    )


@app.put("/api/llm/settings", response_model=LLMSettingsResponse)
def update_llm_settings_endpoint(updates: dict[str, Any]) -> LLMSettingsResponse:
    """Update LLM settings."""
    global llm_settings
    llm_settings = update_llm_settings(updates)

    return LLMSettingsResponse(
        provider=llm_settings.provider,
        providers=[LLMProvider.openai, LLMProvider.claude, LLMProvider.watsonx, LLMProvider.ollama],
        openai=llm_settings.openai.model_dump(),
        claude=llm_settings.claude.model_dump(),
        watsonx=llm_settings.watsonx.model_dump(),
        ollama=llm_settings.ollama.model_dump(),
        enable_llm_extraction=llm_settings.enable_llm_extraction,
        fallback_to_regex=llm_settings.fallback_to_regex,
    )


# ============================================================================
# Model Catalog Endpoints
# ============================================================================

@app.get("/api/llm/models", response_model=ModelListResponse)
def list_models(provider: LLMProvider | None = None) -> ModelListResponse:
    """List available models for a provider."""
    effective_provider = provider or llm_settings.provider

    try:
        models, error = list_models_for_provider(effective_provider, llm_settings)
        return ModelListResponse(provider=effective_provider, models=models, error=error)
    except Exception as e:
        logger.error(f"Error listing models for {effective_provider}: {e}")
        return ModelListResponse(provider=effective_provider, models=[], error=str(e))


@app.get("/api/llm/models/{provider}", response_model=ModelListResponse)
def list_provider_models(provider: LLMProvider) -> ModelListResponse:
    """List available models for a specific provider."""
    try:
        models, error = list_models_for_provider(provider, llm_settings)
        return ModelListResponse(provider=provider, models=models, error=error)
    except Exception as e:
        logger.error(f"Error listing models for {provider}: {e}")
        return ModelListResponse(provider=provider, models=[], error=str(e))


@app.get("/api/llm/model-info/{provider}/{model_id}")
def get_model_info_endpoint(provider: LLMProvider, model_id: str) -> dict[str, Any]:
    """Get detailed information about a specific model."""
    try:
        info = get_model_info(provider, model_id, llm_settings)
        return info
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Chat Completion Endpoint (Direct LLM Access)
# ============================================================================

@app.post("/api/llm/chat", response_model=ChatResponse)
def chat_completion(request: ChatRequest) -> ChatResponse:
    """Send chat completion request to the active LLM provider."""
    global llm_client

    try:
        # Initialize client if needed
        if llm_client is None:
            llm_client = build_llm_client(llm_settings)

        # Send completion request
        content = llm_client.chat_completion(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        config = llm_settings.get_active_config()
        model = getattr(config, "model", getattr(config, "model_id", "unknown"))

        return ChatResponse(
            content=content,
            provider=llm_settings.provider.value,
            model=model,
        )

    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}") from e


# ============================================================================
# Policy Endpoints
# ============================================================================

@app.get("/api/policy")
def get_policy() -> dict[str, Any]:
    """Get current policy configuration."""
    return {
        "version": engine.policy.version,
        "rules": engine.policy.rules,
        "metadata": getattr(engine.policy, "metadata", {}),
    }


@app.get("/api/policy/rules")
def list_rules() -> dict[str, Any]:
    """List all available rules."""
    rules_info = []
    for rule_id in engine.registry._rules:
        rule = engine.registry.get(rule_id)
        rules_info.append(
            {
                "id": rule_id,
                "description": getattr(rule, "description", "No description available"),
            }
        )

    return {
        "total": len(rules_info),
        "rules": rules_info,
    }


# ============================================================================
# Metrics Endpoint
# ============================================================================

@app.get("/metrics")
def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    if not _METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics not enabled (missing prometheus_client)")
    data = generate_latest(registry=_reg)
    return PlainTextResponse(content=data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
