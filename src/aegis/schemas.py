from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Decision(str, Enum):
    """Final gate outcome returned by Aegis."""

    allow = "allow"
    deny = "deny"
    revise = "revise"


class Action(BaseModel):
    """Structured action the system intends to perform.

    Aegis verifies actions rather than free text, so action extraction must
    produce this schema.
    """

    op: str = Field(
        ..., description="Operation name (domain op or tool name)."
    )
    args: Dict[str, Any] = Field(
        default_factory=dict, description="Operation arguments."
    )
    tool: Optional[str] = Field(
        default=None,
        description="Optional tool identifier if the action uses a tool.",
    )
    risk_class: str = Field(
        default="standard",
        description="Risk class (e.g. standard/high). Used to decide fail-open vs fail-closed.",
    )


class Facts(BaseModel):
    """Structured world-state facts used for verification."""

    data: Dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    """A validated, structured representation of user intent."""

    text: str = Field(..., description="Original user text.")
    action: Action
    facts: Facts = Field(default_factory=Facts)
    assumptions: List[str] = Field(default_factory=list)
    prompt_version: Optional[str] = Field(
        default=None, description="Prompt/extractor version used to create the intent."
    )


class RuleHit(BaseModel):
    """Result of a single rule evaluation."""

    rule_id: str
    ok: bool
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class Telemetry(BaseModel):
    """Basic telemetry returned for debugging/ops."""

    latency_ms: Optional[int] = None
    stages_ms: Dict[str, int] = Field(default_factory=dict)


class AegisDecision(BaseModel):
    """The production decision contract for Aegis."""

    decision: Decision
    reason_codes: List[str] = Field(default_factory=list)
    human_message: str
    policy_version: str
    rule_hits: List[RuleHit] = Field(default_factory=list)
    telemetry: Telemetry = Field(default_factory=Telemetry)
    request_id: Optional[str] = None
