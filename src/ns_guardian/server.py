"""
Standalone server entry point for Neuro-Symbolic Guardian.

This module provides a CLI for running the Guardian as either:
1. MCP server (stdio transport)
2. FastAPI REST server
3. CLI verification tool
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from aegis.config import Settings
from aegis.engine import AegisEngine
from aegis.extractors.llm import LLMIntentExtractor
from aegis.extractors.regex_fallback import RegexFallbackExtractor
from aegis.providers.openai_compat import OpenAICompatibleProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_mcp_server() -> None:
    """Run the MCP server."""
    from ns_guardian.mcp_server import main as mcp_main

    logger.info("Starting Neuro-Symbolic Guardian MCP Server")
    mcp_main()


def run_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI REST server."""
    import uvicorn

    logger.info(f"Starting Neuro-Symbolic Guardian API Server on {host}:{port}")
    uvicorn.run("aegis.api.app:app", host=host, port=port, log_level="info")


def run_cli_verify(text: str, facts: dict[str, Any] | None = None) -> None:
    """Run CLI verification."""
    facts = facts or {}

    settings = Settings.from_env()
    engine = AegisEngine(policy=settings.load_policy())
    regex_extractor = RegexFallbackExtractor()

    # Initialize LLM extractor if enabled
    if settings.enable_llm:
        provider = OpenAICompatibleProvider()
        llm_extractor: LLMIntentExtractor | None = LLMIntentExtractor(provider)
    else:
        llm_extractor = None

    # Extract intent
    if llm_extractor is not None:
        try:
            intent = llm_extractor.extract(text, facts=facts)
        except Exception as e:
            logger.warning(f"LLM extraction failed, falling back to regex: {e}")
            intent = regex_extractor.extract(text, facts=facts)
    else:
        intent = regex_extractor.extract(text, facts=facts)

    # Verify
    decision = engine.verify(intent)

    # Output results
    result = {
        "decision": decision.decision.value,
        "message": decision.human_message,
        "reason_codes": decision.reason_codes,
        "policy_version": decision.policy_version,
        "request_id": decision.request_id,
        "rule_hits": [
            {"rule_id": hit.rule_id, "ok": hit.ok, "code": hit.code, "message": hit.message}
            for hit in decision.rule_hits
        ],
        "telemetry": {"latency_ms": decision.telemetry.latency_ms},
    }

    print(json.dumps(result, indent=2))

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Neuro-Symbolic Guardian - Symbolic Logic Layer for LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as MCP server (default)
  ns-guardian

  # Run as API server
  ns-guardian --mode api --host 0.0.0.0 --port 8000

  # Run CLI verification
  ns-guardian --mode cli --text "consume 3 from inventory" --facts '{"inventory": 2}'

Environment Variables:
  AEGIS_ENV              - Environment name (default: dev)
  AEGIS_POLICY_PATH      - Path to policy YAML
  AEGIS_ENABLE_LLM       - Enable LLM extraction (true/false)
  AEGIS_LLM_API_KEY      - LLM API key
  AEGIS_LLM_BASE_URL     - LLM API base URL
  AEGIS_LLM_MODEL        - LLM model name
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["mcp", "api", "cli"],
        default="mcp",
        help="Server mode (default: mcp)",
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)",
    )

    parser.add_argument(
        "--text",
        help="Text to verify (CLI mode only)",
    )

    parser.add_argument(
        "--facts",
        help="Facts JSON string (CLI mode only)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.mode == "mcp":
            run_mcp_server()
        elif args.mode == "api":
            run_api_server(host=args.host, port=args.port)
        elif args.mode == "cli":
            if not args.text:
                parser.error("--text is required for CLI mode")
            facts = json.loads(args.facts) if args.facts else {}
            run_cli_verify(args.text, facts)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
