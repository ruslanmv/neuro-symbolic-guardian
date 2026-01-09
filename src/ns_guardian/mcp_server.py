"""
Neuro-Symbolic Guardian MCP Server

This module implements the Model Context Protocol (MCP) server for the
Neuro-Symbolic Guardian. It exposes tools, resources, and prompts that allow
any MCP-compatible LLM to verify actions using symbolic logic.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

from aegis.config import Settings
from aegis.engine import AegisEngine
from aegis.extractors.llm import LLMIntentExtractor
from aegis.extractors.regex_fallback import RegexFallbackExtractor
from aegis.providers.openai_compat import OpenAICompatibleProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NeurosymbolicGuardianServer:
    """MCP server implementation for the Neuro-Symbolic Guardian."""

    def __init__(self) -> None:
        """Initialize the Guardian MCP server."""
        self.server = Server("neuro-symbolic-guardian")
        self.settings = Settings.from_env()
        self.engine = AegisEngine(policy=self.settings.load_policy())
        self.regex_extractor = RegexFallbackExtractor()

        # Initialize LLM extractor if enabled
        if self.settings.enable_llm:
            provider = OpenAICompatibleProvider()
            self.llm_extractor: LLMIntentExtractor | None = LLMIntentExtractor(provider)
        else:
            self.llm_extractor = None

        # Register handlers
        self._register_tools()
        self._register_resources()
        self._register_prompts()

        logger.info("Neuro-Symbolic Guardian MCP Server initialized")
        logger.info(f"Policy version: {self.engine.policy.version}")
        logger.info(f"LLM extraction enabled: {bool(self.llm_extractor)}")

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="verify_action",
                    description=(
                        "Verify if an action is logically valid and complies with policies. "
                        "Takes natural language text and optional facts, returns allow/deny/revise decision."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Natural language description of the action to verify",
                            },
                            "facts": {
                                "type": "object",
                                "description": "Optional world-state facts (e.g., {'inventory': 5})",
                                "default": {},
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="extract_intent",
                    description=(
                        "Extract structured intent from natural language text. "
                        "Returns a structured representation with action, arguments, and risk classification."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Natural language text to extract intent from",
                            },
                            "facts": {
                                "type": "object",
                                "description": "Optional context facts",
                                "default": {},
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="check_logic",
                    description=(
                        "Perform pure logical constraint checking using Z3 theorem prover. "
                        "Checks if a set of constraints is satisfiable."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "constraints": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of logical constraints (e.g., ['x > 0', 'x < 10'])",
                            },
                            "facts": {
                                "type": "object",
                                "description": "Known facts/variable values",
                                "default": {},
                            },
                        },
                        "required": ["constraints"],
                    },
                ),
                Tool(
                    name="query_policy",
                    description="Get information about the current policy configuration and enabled rules.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": "Optional filter (e.g., 'enabled', 'all')",
                                "default": "enabled",
                            }
                        },
                    },
                ),
                Tool(
                    name="explain_decision",
                    description=(
                        "Get a detailed explanation of why a decision was made, "
                        "including the logical proof or counter-example."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "decision": {
                                "type": "object",
                                "description": "The decision object from verify_action",
                            }
                        },
                        "required": ["decision"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls."""
            try:
                if name == "verify_action":
                    return await self._verify_action(arguments)
                elif name == "extract_intent":
                    return await self._extract_intent(arguments)
                elif name == "check_logic":
                    return await self._check_logic(arguments)
                elif name == "query_policy":
                    return await self._query_policy(arguments)
                elif name == "explain_decision":
                    return await self._explain_decision(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _register_resources(self) -> None:
        """Register MCP resources."""

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri=AnyUrl("policy://current"),
                    name="Current Policy",
                    description="The currently active policy configuration",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("rules://list"),
                    name="Available Rules",
                    description="List of all available verification rules",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("policy://version"),
                    name="Policy Version",
                    description="Current policy version information",
                    mimeType="text/plain",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            """Read a resource."""
            uri_str = str(uri)

            if uri_str == "policy://current":
                return json.dumps(
                    {
                        "version": self.engine.policy.version,
                        "rules": self.engine.policy.rules,
                        "metadata": getattr(self.engine.policy, "metadata", {}),
                    },
                    indent=2,
                )
            elif uri_str == "rules://list":
                rules_info = []
                for rule_id in self.engine.registry._rules:
                    rule = self.engine.registry.get(rule_id)
                    rules_info.append(
                        {
                            "id": rule_id,
                            "description": getattr(rule, "description", "No description available"),
                        }
                    )
                return json.dumps(rules_info, indent=2)
            elif uri_str == "policy://version":
                return self.engine.policy.version
            else:
                raise ValueError(f"Unknown resource: {uri_str}")

    def _register_prompts(self) -> None:
        """Register MCP prompts."""

        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            """List available prompts."""
            return [
                Prompt(
                    name="generate_constraints",
                    description="Generate Z3 logical constraints from natural language requirements",
                    arguments=[
                        PromptArgument(
                            name="requirements",
                            description="Natural language requirements to convert to constraints",
                            required=True,
                        )
                    ],
                ),
                Prompt(
                    name="explain_violation",
                    description="Explain why an action violated policy rules",
                    arguments=[
                        PromptArgument(
                            name="action",
                            description="The action that was denied",
                            required=True,
                        ),
                        PromptArgument(
                            name="rule_hits",
                            description="The rule violations that occurred",
                            required=True,
                        ),
                    ],
                ),
                Prompt(
                    name="suggest_fix",
                    description="Suggest how to modify an action to comply with policies",
                    arguments=[
                        PromptArgument(
                            name="action",
                            description="The original action that was denied",
                            required=True,
                        ),
                        PromptArgument(
                            name="violations",
                            description="The policy violations",
                            required=True,
                        ),
                    ],
                ),
            ]

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
            """Get a prompt."""
            arguments = arguments or {}

            if name == "generate_constraints":
                requirements = arguments.get("requirements", "")
                return GetPromptResult(
                    description="Generate Z3 constraints from requirements",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""You are a formal methods expert. Convert the following natural language requirements into Z3 Python API constraints.

Requirements:
{requirements}

Generate Python code using the Z3 API that expresses these requirements as logical constraints. Use clear variable names and add comments explaining each constraint.

Example format:
```python
from z3 import *

# Define variables
x = Int('x')
inventory = Int('inventory')

# Define constraints
solver = Solver()
solver.add(inventory >= 0)  # Inventory must be non-negative
solver.add(x <= inventory)  # Cannot consume more than available

# Check satisfiability
result = solver.check()
if result == sat:
    print("Constraints are satisfiable")
    print(solver.model())
else:
    print("Constraints are unsatisfiable")
```""",
                            ),
                        )
                    ],
                )

            elif name == "explain_violation":
                action = arguments.get("action", "")
                rule_hits = arguments.get("rule_hits", "")
                return GetPromptResult(
                    description="Explain policy violation",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Explain why the following action was denied by the Neuro-Symbolic Guardian:

Action: {action}

Rule Violations:
{rule_hits}

Provide a clear, non-technical explanation suitable for a user. Explain:
1. What the action was trying to do
2. Which policy rules were violated and why
3. The logical reasoning behind the denial
4. Any security or safety implications""",
                            ),
                        )
                    ],
                )

            elif name == "suggest_fix":
                action = arguments.get("action", "")
                violations = arguments.get("violations", "")
                return GetPromptResult(
                    description="Suggest fix for policy violation",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""The following action was denied due to policy violations:

Action: {action}

Violations:
{violations}

Suggest specific modifications to make this action compliant. Provide:
1. A revised version of the action that would be allowed
2. Step-by-step changes needed
3. Alternative approaches if the original intent cannot be fulfilled
4. Any additional considerations or best practices""",
                            ),
                        )
                    ],
                )

            else:
                raise ValueError(f"Unknown prompt: {name}")

    async def _verify_action(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Verify an action."""
        text = arguments.get("text", "")
        facts = arguments.get("facts", {})

        # Extract intent
        if self.llm_extractor is not None:
            try:
                intent = self.llm_extractor.extract(text, facts=facts)
            except Exception:
                intent = self.regex_extractor.extract(text, facts=facts)
        else:
            intent = self.regex_extractor.extract(text, facts=facts)

        # Verify intent
        decision = self.engine.verify(intent)

        # Format response
        result = {
            "decision": decision.decision.value,
            "reason_codes": decision.reason_codes,
            "message": decision.human_message,
            "policy_version": decision.policy_version,
            "request_id": decision.request_id,
            "telemetry": {
                "latency_ms": decision.telemetry.latency_ms,
                "stages_ms": decision.telemetry.stages_ms,
            },
            "rule_hits": [
                {
                    "rule_id": hit.rule_id,
                    "ok": hit.ok,
                    "code": hit.code,
                    "message": hit.message,
                    "details": hit.details,
                }
                for hit in decision.rule_hits
            ],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _extract_intent(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Extract intent from text."""
        text = arguments.get("text", "")
        facts = arguments.get("facts", {})

        if self.llm_extractor is not None:
            try:
                intent = self.llm_extractor.extract(text, facts=facts)
            except Exception:
                intent = self.regex_extractor.extract(text, facts=facts)
        else:
            intent = self.regex_extractor.extract(text, facts=facts)

        result = {
            "text": intent.text,
            "action": {
                "op": intent.action.op,
                "args": intent.action.args,
                "tool": intent.action.tool,
                "risk_class": intent.action.risk_class,
            },
            "facts": intent.facts.data,
            "assumptions": intent.assumptions,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _check_logic(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Check logical constraints using Z3."""
        from z3 import Bool, Int, Solver, sat

        constraints = arguments.get("constraints", [])
        facts = arguments.get("facts", {})

        try:
            solver = Solver()

            # Create a simple namespace for evaluation
            namespace: dict[str, Any] = {"Int": Int, "Bool": Bool, "solver": solver, **facts}

            # Add constraints
            for constraint in constraints:
                # Parse and add constraint
                # This is a simplified version - production would need more sophisticated parsing
                solver.add(eval(constraint, namespace))

            # Check satisfiability
            result = solver.check()

            if result == sat:
                model = solver.model()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "satisfiable": True,
                                "model": str(model),
                                "message": "All constraints are satisfiable",
                            },
                            indent=2,
                        ),
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "satisfiable": False,
                                "message": "Constraints are unsatisfiable",
                                "unsat_core": "No valid solution exists",
                            },
                            indent=2,
                        ),
                    )
                ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": str(e), "message": "Failed to check constraints"}, indent=2
                    ),
                )
            ]

    async def _query_policy(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Query policy information."""
        filter_type = arguments.get("filter", "enabled")

        rules = []
        for rule_cfg in self.engine.policy.rules:
            if filter_type == "all" or (filter_type == "enabled" and rule_cfg.get("enabled", True)):
                rules.append(rule_cfg)

        result = {
            "policy_version": self.engine.policy.version,
            "total_rules": len(self.engine.policy.rules),
            "enabled_rules": len([r for r in self.engine.policy.rules if r.get("enabled", True)]),
            "rules": rules,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _explain_decision(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Explain a decision."""
        decision = arguments.get("decision", {})

        explanation = {
            "decision": decision.get("decision", "unknown"),
            "explanation": decision.get("message", ""),
            "violated_rules": [],
            "reasoning": [],
        }

        # Parse rule hits
        for hit in decision.get("rule_hits", []):
            if not hit.get("ok", True):
                explanation["violated_rules"].append(
                    {"rule": hit.get("rule_id", ""), "reason": hit.get("message", "")}
                )

        # Generate reasoning
        if decision.get("decision") == "deny":
            explanation["reasoning"].append(
                "The action was denied because it would violate logical constraints or security policies."
            )
        elif decision.get("decision") == "revise":
            explanation["reasoning"].append(
                "The action needs revision to comply with policies. Modify the parameters and try again."
            )
        else:
            explanation["reasoning"].append("The action passed all policy checks and logical constraints.")

        return [TextContent(type="text", text=json.dumps(explanation, indent=2))]


def main() -> None:
    """Run the MCP server."""
    import asyncio

    async def run() -> None:
        """Run the server."""
        guardian = NeurosymbolicGuardianServer()
        async with stdio_server() as (read_stream, write_stream):
            await guardian.server.run(read_stream, write_stream, guardian.server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
