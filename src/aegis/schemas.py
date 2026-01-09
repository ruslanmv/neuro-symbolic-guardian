from __future__ import annotations

from enum import Enum
from typing import Any

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
    args: dict[str, Any] = Field(
        default_factory=dict, description="Operation arguments."
    )
    tool: str | None = Field(
        default=None,
        description="Optional tool identifier if the action uses a tool.",
    )
    risk_class: str = Field(
        default="standard",
        description="Risk class (e.g. standard/high). Used to decide fail-open vs fail-closed.",
    )


class Facts(BaseModel):
    """Structured world-state facts used for verification."""

    data: dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    """A validated, structured representation of user intent."""

    text: str = Field(..., description="Original user text.")
    action: Action
    facts: Facts = Field(default_factory=Facts)
    assumptions: list[str] = Field(default_factory=list)
    prompt_version: str | None = Field(
        default=None, description="Prompt/extractor version used to create the intent."
    )


class RuleHit(BaseModel):
    """Result of a single rule evaluation."""

    rule_id: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Telemetry(BaseModel):
    """Basic telemetry returned for debugging/ops."""

    latency_ms: int | None = None
    stages_ms: dict[str, int] = Field(default_factory=dict)


class AegisDecision(BaseModel):
    """The production decision contract for Aegis."""

    decision: Decision
    reason_codes: list[str] = Field(default_factory=list)
    human_message: str
    policy_version: str
    rule_hits: list[RuleHit] = Field(default_factory=list)
    telemetry: Telemetry = Field(default_factory=Telemetry)
    request_id: str | None = None
