"""Deprecated CLI entrypoint.

The project has been renamed to **Aegis**.
This module remains for backward compatibility with the original `ns-guardian`
console script.
"""

from __future__ import annotations

from aegis.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
