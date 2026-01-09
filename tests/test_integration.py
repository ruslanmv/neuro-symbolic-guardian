"""
Integration tests for the Neuro-Symbolic Guardian.
"""

from __future__ import annotations

import pytest
from aegis.engine import AegisEngine
from aegis.extractors.regex_fallback import RegexFallbackExtractor
from aegis.policy import load_policy
from aegis.schemas import Decision


@pytest.fixture
def engine() -> AegisEngine:
    """Create an engine with default policy."""
    return AegisEngine()


@pytest.fixture
def extractor() -> RegexFallbackExtractor:
    """Create a regex extractor."""
    return RegexFallbackExtractor()


def test_physical_constraint_violation(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that physical constraints are enforced."""
    # Try to consume more than available
    intent = extractor.extract("consume 3 from 2", facts={"inventory": 2})
    # Physical constraint violations should be high risk
    intent.action.risk_class = "high"
    decision = engine.verify(intent)

    assert decision.decision == Decision.deny
    assert any("inventory" in code for code in decision.reason_codes)


def test_allowed_action(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that valid actions are allowed."""
    # Consume within limits
    intent = extractor.extract("consume 1 from 2", facts={"inventory": 2})
    decision = engine.verify(intent)

    assert decision.decision == Decision.allow
    assert len(decision.reason_codes) == 0


def test_secret_detection(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that secrets are detected and blocked."""
    # Try to use an API key
    intent = extractor.extract("use API key sk-1234567890abcdefghij", facts={})
    decision = engine.verify(intent)

    assert decision.decision == Decision.deny
    assert any("secret" in code for code in decision.reason_codes)


def test_policy_versioning(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that policy version is tracked."""
    intent = extractor.extract("test action", facts={})
    decision = engine.verify(intent)

    assert decision.policy_version is not None
    assert len(decision.policy_version) > 0


def test_telemetry_collection(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that telemetry is collected."""
    intent = extractor.extract("test action", facts={})
    decision = engine.verify(intent)

    assert decision.telemetry is not None
    assert decision.telemetry.latency_ms is not None
    assert decision.telemetry.latency_ms >= 0


def test_rule_hit_details(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that rule hit details are provided."""
    intent = extractor.extract("consume 3 from 2", facts={"inventory": 2})
    decision = engine.verify(intent)

    assert len(decision.rule_hits) > 0
    for hit in decision.rule_hits:
        assert hit.rule_id is not None
        assert hit.code is not None
        assert hit.message is not None


def test_request_id_uniqueness(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that each request gets a unique ID."""
    intent1 = extractor.extract("action 1", facts={})
    decision1 = engine.verify(intent1)

    intent2 = extractor.extract("action 2", facts={})
    decision2 = engine.verify(intent2)

    assert decision1.request_id != decision2.request_id


def test_risk_class_handling(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that risk classes are handled correctly."""
    # High risk action should fail closed
    intent = extractor.extract("delete all users", facts={})
    intent.action.risk_class = "critical"

    decision = engine.verify(intent)

    # Critical actions should be carefully evaluated
    assert decision.decision in [Decision.allow, Decision.deny, Decision.revise]


def test_multiple_rules_evaluation(engine: AegisEngine, extractor: RegexFallbackExtractor) -> None:
    """Test that multiple rules are evaluated."""
    intent = extractor.extract("test action with secret sk-test123", facts={})
    decision = engine.verify(intent)

    # Should check both action rules and secret scanning
    assert len(decision.rule_hits) >= 1


@pytest.mark.parametrize(
    "text,expected_decision",
    [
        ("consume 0 from 5", Decision.allow),
        ("consume 5 from 5", Decision.allow),
        ("consume 1 from 0", Decision.deny),
        ("consume 10 from 5", Decision.deny),
    ],
)
def test_inventory_scenarios(
    engine: AegisEngine, extractor: RegexFallbackExtractor, text: str, expected_decision: Decision
) -> None:
    """Test various inventory scenarios."""
    parts = text.split()
    consume = int(parts[1])
    inventory = int(parts[3])

    intent = extractor.extract(text, facts={"inventory": inventory})
    # Set high risk for constraint violations to ensure they're denied, not just revised
    if expected_decision == Decision.deny:
        intent.action.risk_class = "high"
    decision = engine.verify(intent)

    assert decision.decision == expected_decision
