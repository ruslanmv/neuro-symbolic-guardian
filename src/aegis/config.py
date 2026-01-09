from __future__ import annotations

import os
from dataclasses import dataclass

from .policy import Policy, default_policy_path, load_policy


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables.

    Keep settings minimal; in production, use a secret manager for credentials.
    """

    env: str
    policy_path: str | None
    enable_llm: bool

    @staticmethod
    def from_env() -> Settings:
        env = os.getenv("AEGIS_ENV", "dev")
        policy_path = os.getenv("AEGIS_POLICY_PATH")
        enable_llm = os.getenv("AEGIS_ENABLE_LLM", "0").lower() in {"1", "true", "yes"}
        return Settings(env=env, policy_path=policy_path, enable_llm=enable_llm)

    def load_policy(self) -> Policy:
        path = self.policy_path or str(default_policy_path())
        return load_policy(path)
