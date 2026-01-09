from __future__ import annotations

import argparse
import json
import sys

from .config import Settings
from .engine import AegisEngine
from .extractors.regex_fallback import RegexFallbackExtractor


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(prog="aegis", description="Aegis: neuro-symbolic verification gate")
    parser.add_argument("text", nargs="?", help="User text to verify")
    parser.add_argument("--facts", default="{}", help="JSON dict of facts/context")
    parser.add_argument("--policy", default=None, help="Path to policy YAML")

    args = parser.parse_args(argv)

    text = args.text or ""
    try:
        facts = json.loads(args.facts)
        if not isinstance(facts, dict):
            raise ValueError
    except Exception:
        return 2

    settings = Settings.from_env()
    if args.policy:
        settings = Settings(env=settings.env, policy_path=args.policy, enable_llm=settings.enable_llm)

    engine = AegisEngine(policy=settings.load_policy())
    extractor = RegexFallbackExtractor()
    intent = extractor.extract(text, facts=facts)
    engine.verify(intent)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
