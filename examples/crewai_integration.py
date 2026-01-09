"""
Example: Using Neuro-Symbolic Guardian with CrewAI

This example shows how to integrate the Guardian with CrewAI agents
to add symbolic verification to agentic workflows.
"""

from __future__ import annotations

import asyncio

try:
    from crewai import Agent, Crew, Process, Task

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

from aegis.engine import AegisEngine
from aegis.extractors.regex_fallback import RegexFallbackExtractor
from aegis.llm_providers import build_crewai_llm
from aegis.llm_settings import get_llm_settings
from aegis.schemas import Decision


class GuardianVerifiedAgent:
    """
    A CrewAI agent wrapped with Guardian verification.

    All actions proposed by the agent are verified against policies
    before execution.
    """

    def __init__(self, role: str, goal: str, backstory: str) -> None:
        """Initialize a Guardian-verified agent."""
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI is not installed")

        self.role = role
        self.goal = goal
        self.backstory = backstory

        # Initialize Guardian components
        self.engine = AegisEngine()
        self.extractor = RegexFallbackExtractor()

        # Get LLM settings and build CrewAI-compatible LLM
        self.llm_settings = get_llm_settings()
        self.llm = build_crewai_llm(self.llm_settings)

        # Create CrewAI agent
        self.agent = Agent(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            llm=self.llm,
            verbose=True,
        )

    def verify_action(self, action_description: str, facts: dict[str, any] = None) -> tuple[bool, str]:
        """
        Verify an action using the Guardian.

        Args:
            action_description: Natural language description of the action
            facts: Optional facts about the world state

        Returns:
            Tuple of (allowed, reason)
        """
        facts = facts or {}

        # Extract intent
        intent = self.extractor.extract(action_description, facts=facts)

        # Verify with Guardian
        decision = self.engine.verify(intent)

        if decision.decision == Decision.allow:
            return True, "Action allowed"
        elif decision.decision == Decision.deny:
            return False, decision.human_message
        else:  # revise
            return False, f"Action needs revision: {decision.human_message}"

    def execute_task_with_verification(self, task_description: str, facts: dict[str, any] = None) -> str:
        """
        Execute a task with Guardian verification.

        Args:
            task_description: Description of the task
            facts: Optional world-state facts

        Returns:
            Task result
        """
        # Create task
        task = Task(
            description=task_description,
            expected_output="A complete response to the task",
            agent=self.agent,
        )

        # Create crew
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        # Execute
        result = crew.kickoff()

        # Extract result text
        result_text = result.raw if hasattr(result, "raw") else str(result)

        # Verify the result
        allowed, reason = self.verify_action(result_text, facts)

        if not allowed:
            return f"⛔ Action blocked by Guardian: {reason}"

        return f"✅ Action verified and allowed:\n{result_text}"


async def example_inventory_management() -> None:
    """Example: Inventory management with Guardian verification."""

    # Create a Guardian-verified agent
    agent = GuardianVerifiedAgent(
        role="Inventory Manager",
        goal="Manage inventory operations safely and correctly",
        backstory=(
            "You are an experienced inventory manager who ensures all "
            "operations follow physical constraints and business rules."
        ),
    )

    # Test 1: Valid operation
    agent.execute_task_with_verification(
        "Process order: consume 2 items from inventory", facts={"inventory": 5}
    )

    # Test 2: Invalid operation (would result in negative inventory)
    agent.execute_task_with_verification(
        "Process order: consume 10 items from inventory", facts={"inventory": 5}
    )


async def example_security_operations() -> None:
    """Example: Security operations with Guardian verification."""

    agent = GuardianVerifiedAgent(
        role="Security Engineer",
        goal="Perform security operations safely",
        backstory="You are a security engineer who follows strict security policies.",
    )

    # Test 1: Trying to expose API key (should be blocked)
    agent.execute_task_with_verification(
        "Configure API with key: sk-1234567890abcdefghij",
        facts={},
    )

    # Test 2: Safe configuration
    agent.execute_task_with_verification(
        "Configure API with environment variable reference",
        facts={},
    )


async def example_multi_agent_workflow() -> None:
    """Example: Multi-agent workflow with Guardian oversight."""
    if not CREWAI_AVAILABLE:
        return


    # Create multiple agents
    planner = GuardianVerifiedAgent(
        role="Planning Agent",
        goal="Create safe and compliant action plans",
        backstory="You create detailed plans that comply with all policies.",
    )

    executor = GuardianVerifiedAgent(
        role="Execution Agent",
        goal="Execute approved plans safely",
        backstory="You execute plans while respecting all constraints.",
    )

    # Planner creates a plan
    planner.execute_task_with_verification(
        "Create a plan to update inventory by reducing 3 items",
        facts={"inventory": 10},
    )

    # Executor attempts to execute
    executor.execute_task_with_verification(
        "Execute plan: reduce inventory by 3 items",
        facts={"inventory": 10},
    )


def main() -> None:
    """Run all examples."""

    if not CREWAI_AVAILABLE:
        return

    # Check LLM configuration
    llm_settings = get_llm_settings()
    config = llm_settings.get_active_config()
    api_key = getattr(config, "api_key", None)

    if not api_key:
        return


    # Run examples
    asyncio.run(example_inventory_management())
    asyncio.run(example_security_operations())
    asyncio.run(example_multi_agent_workflow())



if __name__ == "__main__":
    main()
