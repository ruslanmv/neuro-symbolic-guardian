#!/usr/bin/env bash
set -euo pipefail

# Simple local bootstrap helper
# Usage: ./scripts/bootstrap.sh

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .

echo "✅ Installed. Run: make run"
