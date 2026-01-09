# Aegis

Aegis is a **neuro-symbolic verification and policy enforcement layer** for LLM systems.
It turns *free-text* requests into **structured intents**, verifies them against **versioned policies** (incl. Z3/SAT constraints), and returns a **standard production decision contract**:

- `allow` – safe to execute/respond
- `revise` – intent/output must be changed
- `deny` – blocked (high risk, secrets detected, or solver uncertainty)

> This repository evolved from the earlier *neuro-symbolic-guardian* prototype. The original `ns-guardian` CLI remains as a compatibility shim.

## Why Aegis

LLM apps fail in predictable ways: violating domain invariants, tool misuse, leaking secrets, and drifting policies. Aegis provides a reliable *"extract → verify → gate"* layer with:

- **Strict schema validation** (Pydantic)
- **Versioned policies** (YAML)
- **Rule registry** (extendable)
- **Symbolic checks** (Z3) + deterministic timeouts
- **API service** (FastAPI) + optional Prometheus metrics

## Quickstart

### Install

```bash
pip install -e .
```

### CLI

```bash
aegis "I have 2 apples. consume 3 from 2" --facts '{"inventory":2}'
```

### Run API

```bash
uvicorn aegis.api.app:app --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl -s http://localhost:8000/verify \
  -X POST \
  -H 'content-type: application/json' \
  -d '{"text": "consume 3 from 2", "facts": {"inventory": 2}}' | jq
```

## Environment variables

- `AEGIS_ENV` – environment name (default: `dev`)
- `AEGIS_POLICY_PATH` – path to a policy YAML (default: built-in default policy)
- `AEGIS_ENABLE_LLM` – enable LLM-backed extraction (`1`/`true`)

LLM provider (OpenAI-compatible):
- `AEGIS_LLM_BASE_URL` (default: `https://api.openai.com`)
- `AEGIS_LLM_API_KEY` (required if LLM enabled)
- `AEGIS_LLM_MODEL` (default: `gpt-4o-mini`)

## Policy format

Policies live in `src/aegis/policies/*.yaml`:

```yaml
version: "1.0.0"
rules:
  - id: "inventory.non_negative"
    enabled: true
    params:
      timeout_ms: 50
```

## Extending rules

Add a new rule under `src/aegis/rules/` that implements:

- `rule_id: str`
- `evaluate(intent, params) -> RuleHit`

Then register it in `AegisEngine.__init__` (or add plugin loading later).

## Production notes

This repo includes production building blocks, but deployment details depend on your environment:

- run behind a gateway (TLS, authn/authz)
- store policies in a controlled artifact repo
- configure audit logging and retention
- consider fail-open/closed per risk class
- add load tests for your rule set

## License

Apache 2.0
