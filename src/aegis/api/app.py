from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from ..config import Settings
from ..engine import AegisEngine
from ..extractors.llm import LLMIntentExtractor
from ..extractors.regex_fallback import RegexFallbackExtractor
from ..providers.openai_compat import OpenAICompatibleProvider
from ..schemas import AegisDecision, Intent

try:
    from prometheus_client import CONTENT_TYPE_LATEST, GeneratorRegistry, generate_latest
    from prometheus_client import Counter, Histogram

    _METRICS_ENABLED = True
except Exception:  # pragma: no cover
    _METRICS_ENABLED = False


app = FastAPI(title="Aegis", version="1.0.0")

settings = Settings.from_env()
engine = AegisEngine(policy=settings.load_policy())
regex_extractor = RegexFallbackExtractor()

if settings.enable_llm:
    provider = OpenAICompatibleProvider()
    llm_extractor: Optional[LLMIntentExtractor] = LLMIntentExtractor(provider)
else:
    llm_extractor = None

if _METRICS_ENABLED:
    _reg = GeneratorRegistry()
    REQUESTS = Counter("aegis_requests_total", "Total Aegis requests", ["endpoint", "decision"], registry=_reg)
    LATENCY = Histogram("aegis_latency_ms", "Aegis request latency (ms)", ["endpoint"], registry=_reg)


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> Dict[str, Any]:
    return {"status": "ready", "policy_version": engine.policy.version, "llm_enabled": bool(llm_extractor)}


@app.post("/extract_intent", response_model=Intent)
def extract_intent(payload: Dict[str, Any]) -> Intent:
    text = str(payload.get("text", ""))
    facts = payload.get("facts", {})
    if not isinstance(facts, dict):
        raise HTTPException(status_code=400, detail="facts must be an object")

    if llm_extractor is not None:
        try:
            return llm_extractor.extract(text, facts=facts)
        except Exception:
            # fail-safe: fall back to regex
            return regex_extractor.extract(text, facts=facts)

    return regex_extractor.extract(text, facts=facts)


@app.post("/verify", response_model=AegisDecision)
def verify(payload: Dict[str, Any]) -> AegisDecision:
    try:
        intent = Intent.model_validate(payload.get("intent")) if "intent" in payload else extract_intent(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid intent payload: {e}")

    endpoint = "/verify"
    if _METRICS_ENABLED:
        with LATENCY.labels(endpoint=endpoint).time():
            decision = engine.verify(intent)
    else:
        decision = engine.verify(intent)

    if _METRICS_ENABLED:
        REQUESTS.labels(endpoint=endpoint, decision=str(decision.decision.value)).inc()

    return decision


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    if not _METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics not enabled (missing prometheus_client)")
    data = generate_latest(registry=_reg)
    return PlainTextResponse(content=data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
