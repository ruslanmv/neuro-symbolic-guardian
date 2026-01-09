SHELL := /bin/bash
PY := python3
VENV := .venv

.PHONY: help venv install run api test clean distclean

help:
	@echo "Targets:"
	@echo "  make venv      - create local virtualenv in $(VENV)"
	@echo "  make install   - install runtime + dev deps"
	@echo "  make run       - run the Aegis CLI (demo)"
	@echo "  make api       - run the Aegis API (FastAPI)"
	@echo "  make test      - run unit tests"
	@echo "  make clean     - remove build/test artifacts"
	@echo "  make distclean - remove virtualenv too"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(VENV)/bin/pip install --upgrade pip setuptools wheel

install: venv
	@$(VENV)/bin/pip install -r requirements.txt
	@$(VENV)/bin/pip install -e .

run: install
	@$(VENV)/bin/aegis "consume 3 from 2" --facts '{"inventory":2}'

api: install
	@$(VENV)/bin/uvicorn aegis.api.app:app --host 0.0.0.0 --port 8000

test: install
	@$(VENV)/bin/pytest

clean:
	@rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__
	@find . -name "*.pyc" -delete || true
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + || true
	@rm -rf build dist *.egg-info

distclean: clean
	@rm -rf $(VENV)
