from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Policy:
    """Loaded policy bundle.

    Policies are versioned and contain enabled rule configurations.
    """

    version: str
    rules: list[dict[str, Any]]
    metadata: dict[str, Any]


def load_policy(path: str | Path) -> Policy:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    version = str(data.get("version", "0"))
    rules = data.get("rules", []) or []
    metadata = data.get("metadata", {}) or {}

    if not isinstance(rules, list):
        raise ValueError("policy.rules must be a list")

    return Policy(version=version, rules=rules, metadata=metadata)


def default_policy_path() -> Path:
    return Path(__file__).with_suffix("").parent / "policies" / "default.yaml"
