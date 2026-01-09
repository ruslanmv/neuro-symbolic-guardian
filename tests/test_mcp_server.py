"""
Tests for the MCP server implementation.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from ns_guardian.mcp_server import NeurosymbolicGuardianServer


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock settings."""
    settings = MagicMock()
    settings.enable_llm = False
    return settings


@pytest.fixture
def mock_engine() -> MagicMock:
    """Mock engine."""
    engine = MagicMock()
    engine.policy.version = "2.0.0"
    engine.policy.rules = []
    return engine


@pytest.fixture
def guardian_server(mock_settings: MagicMock, mock_engine: MagicMock) -> NeurosymbolicGuardianServer:
    """Create a guardian server for testing."""
    with patch("ns_guardian.mcp_server.Settings.from_env", return_value=mock_settings):
        with patch("ns_guardian.mcp_server.AegisEngine", return_value=mock_engine):
            server = NeurosymbolicGuardianServer()
            return server


@pytest.mark.asyncio
async def test_verify_action_allow(guardian_server: NeurosymbolicGuardianServer) -> None:
    """Test verify_action with allowed action."""
    # Mock the engine response
    mock_decision = MagicMock()
    mock_decision.decision.value = "allow"
    mock_decision.reason_codes = []
    mock_decision.human_message = "Action allowed"
    mock_decision.policy_version = "2.0.0"
    mock_decision.request_id = "test-123"
    mock_decision.telemetry.latency_ms = 10
    mock_decision.telemetry.stages_ms = {}
    mock_decision.rule_hits = []

    guardian_server.engine.verify = MagicMock(return_value=mock_decision)

    # Call verify_action
    result = await guardian_server._verify_action({"text": "read from inventory", "facts": {}})

    # Verify result
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    data = json.loads(result[0].text)
    assert data["decision"] == "allow"
    assert data["message"] == "Action allowed"


@pytest.mark.asyncio
async def test_verify_action_deny(guardian_server: NeurosymbolicGuardianServer) -> None:
    """Test verify_action with denied action."""
    # Mock the engine response
    mock_decision = MagicMock()
    mock_decision.decision.value = "deny"
    mock_decision.reason_codes = ["inventory.negative_result"]
    mock_decision.human_message = "Action denied"
    mock_decision.policy_version = "2.0.0"
    mock_decision.request_id = "test-456"
    mock_decision.telemetry.latency_ms = 15
    mock_decision.telemetry.stages_ms = {}
    mock_decision.rule_hits = [
        MagicMock(
            rule_id="inventory.non_negative",
            ok=False,
            code="inventory.negative_result",
            message="Would result in negative inventory",
            details={},
        )
    ]

    guardian_server.engine.verify = MagicMock(return_value=mock_decision)

    # Call verify_action
    result = await guardian_server._verify_action({"text": "consume 3 from 2", "facts": {"inventory": 2}})

    # Verify result
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data["decision"] == "deny"
    assert "inventory.negative_result" in data["reason_codes"]


@pytest.mark.asyncio
async def test_extract_intent(guardian_server: NeurosymbolicGuardianServer) -> None:
    """Test extract_intent."""
    # Mock the extractor
    mock_intent = MagicMock()
    mock_intent.text = "consume 3 apples"
    mock_intent.action.op = "consume"
    mock_intent.action.args = {"quantity": 3, "item": "apples"}
    mock_intent.action.tool = None
    mock_intent.action.risk_class = "standard"
    mock_intent.facts.data = {}
    mock_intent.assumptions = []

    guardian_server.regex_extractor.extract = MagicMock(return_value=mock_intent)

    # Call extract_intent
    result = await guardian_server._extract_intent({"text": "consume 3 apples", "facts": {}})

    # Verify result
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data["text"] == "consume 3 apples"
    assert data["action"]["op"] == "consume"
    assert data["action"]["args"]["quantity"] == 3


@pytest.mark.asyncio
async def test_check_logic_satisfiable() -> None:
    """Test check_logic with satisfiable constraints."""
    with patch("ns_guardian.mcp_server.Settings.from_env"):
        with patch("ns_guardian.mcp_server.AegisEngine"):
            server = NeurosymbolicGuardianServer()

            # Test satisfiable constraints
            result = await server._check_logic({"constraints": ["x > 0", "x < 10"], "facts": {}})

            assert len(result) == 1
            data = json.loads(result[0].text)
            # Note: This might fail depending on Z3 availability in test environment
            assert "satisfiable" in data


@pytest.mark.asyncio
async def test_query_policy(guardian_server: NeurosymbolicGuardianServer) -> None:
    """Test query_policy."""
    guardian_server.engine.policy.rules = [
        {"id": "rule1", "enabled": True},
        {"id": "rule2", "enabled": False},
    ]

    # Query enabled rules
    result = await guardian_server._query_policy({"filter": "enabled"})

    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data["policy_version"] == "2.0.0"
    assert data["total_rules"] == 2
    assert data["enabled_rules"] == 1


@pytest.mark.asyncio
async def test_explain_decision(guardian_server: NeurosymbolicGuardianServer) -> None:
    """Test explain_decision."""
    decision_data = {
        "decision": "deny",
        "message": "Action denied",
        "rule_hits": [{"rule_id": "test_rule", "ok": False, "message": "Test violation"}],
    }

    result = await guardian_server._explain_decision({"decision": decision_data})

    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data["decision"] == "deny"
    assert len(data["violated_rules"]) == 1
    assert data["violated_rules"][0]["rule"] == "test_rule"


def test_server_initialization() -> None:
    """Test server initialization."""
    with patch("ns_guardian.mcp_server.Settings.from_env"):
        with patch("ns_guardian.mcp_server.AegisEngine"):
            server = NeurosymbolicGuardianServer()
            assert server.server is not None
            assert server.engine is not None
            assert server.regex_extractor is not None
