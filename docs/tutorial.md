---
title: "Stop Trying to Prompt Engineer Your Way Out of Hallucinations"
excerpt: "Enterprises don't need more guardrails. They need mathematical verification: a neuro-symbolic 'System 2' gate in front of LLM actions."
tags: [AI Safety, Enterprise AI, Neuro-Symbolic, LLM Governance, MCP]
toc: true
---

## The Enterprise Fear: One Hallucination Away from a Sev-1

Enterprises are stuck. They have amazing models—but they can't deploy them broadly, because **one hallucination** can:

- move money that doesn't exist,
- violate a policy (PCI, GDPR, SOC2 controls),
- leak secrets or PII,
- execute a destructive action (delete, overwrite, public bucket, etc.).

And here's the uncomfortable question:

$$
\textbf{If one failure costs \$10M, why is "probably correct" acceptable?}
$$

---

## The Fallacy: "Guardrails" Can't Fix Logic

Regex filters, prompt rules, keyword blocks—these treat hallucinations like a **text problem**.

But most enterprise failures are **logic failures**.

For example, in banking:

- Available balance: $B = 3200$
- Transfer requested: $T = 10000$

The constraint is not "don't say naughty words."

It's:

$$
T \le B
$$

No prompt can reliably enforce that under adversarial or simply messy real-world inputs.

So the real question is:

$$
\textbf{Can we prove } \forall \text{actions } a,\;\; \text{Constraints}(a)=\text{True} \;?
$$

---

## The Enterprise Solution: "System 2" for LLMs

**Neuro-Symbolic Guardian** is a production-oriented "prefrontal cortex" that sits between users/agents and the model.

- **System 1 (Fast):** LLM (or fallback parser) extracts intent
- **System 2 (Slow):** Z3 theorem prover verifies constraints
- **Decision contract:** `allow` / `revise` / `deny`

### The Red Light / Green Light flow (deterministic)

```mermaid
flowchart TD
  U[User / Agent] --> LLM[System 1: Intent extraction\n(LLM or regex fallback)]
  LLM --> I[Structured Intent]
  I --> Z3[System 2: Z3 verification\n(symbolic constraints)]
  Z3 -->|SAT| G[GREEN: allow]
  Z3 -->|UNSAT| R[RED: deny]
  Z3 -->|Needs changes| Y[YELLOW: revise]
  R --> EX[Explain + Suggest fix]
  Y --> EX
  G --> ACT[Execute / Respond]
```

---

## The Demo: "Transfer More Money Than I Have"

An LLM will often comply:

> "Sure! I've completed the transfer."

But the Guardian evaluates:

$$
T = 10000,\;\; B = 3200,\;\; \text{require } T \le B
$$

Z3 returns **UNSAT** → **RED LIGHT** → action blocked.

This is the point:

$$
\textbf{Math doesn't hallucinate.}
$$

---

# Setup, Installation, and End-to-End Usage

Everything below is tested and verified on the `neuro-symbolic-guardian` project (Python 3.11+, FastAPI, Z3, MCP).

---

## 0) Prerequisites

* Python **3.11+**
* (Optional) Docker / Kubernetes
* (Optional) An LLM API key (OpenAI-compatible). The Guardian can still run without LLM extraction using regex fallback.

---

## 1) Install (UV recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone
git clone https://github.com/ruslanmv/neuro-symbolic-guardian.git
cd neuro-symbolic-guardian

# Create venv + install editable (dev extras include tests/lint)
uv venv --python 3.11
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Install (pip alternative)

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install package
pip install -e ".[dev]"
```

---

## 2) Configure environment

The project supports `.env` files and environment variables.

### Minimal setup (no LLM, regex fallback only):

```bash
export AEGIS_ENV=dev
export AEGIS_POLICY_PATH=./src/aegis/policies/default.yaml
export AEGIS_FAIL_MODE=closed
```

### Enable LLM-based intent extraction (optional):

```bash
export AEGIS_ENABLE_LLM=true
export AEGIS_LLM_BASE_URL=https://api.openai.com/v1
export AEGIS_LLM_API_KEY="YOUR_KEY"
export AEGIS_LLM_MODEL="gpt-4o-mini"

# Timeouts (milliseconds)
export AEGIS_SOLVER_TIMEOUT=100
export AEGIS_LLM_TIMEOUT=5000
```

**Note:** Without an LLM API key, the system automatically falls back to regex-based extraction, which still provides symbolic verification.

---

## 3) Run it

### Option A — CLI Mode (Quick Test)

Perfect for testing the system quickly:

```bash
ns-guardian --mode cli \
  --text "consume 3 from 2" \
  --facts '{"inventory": 2}'
```

**Example Output:**
```json
{
  "decision": "revise",
  "message": "Needs revision: policy checks failed.",
  "reason_codes": ["inventory.would_go_negative"],
  "policy_version": "1.0.0",
  "request_id": "...",
  "rule_hits": [{
    "rule_id": "inventory.non_negative",
    "ok": false,
    "code": "inventory.would_go_negative",
    "message": "Operation 'consume' would violate non-negative inventory."
  }],
  "telemetry": {"latency_ms": 17}
}
```

---

### Option B — REST API Server (Production Mode)

```bash
ns-guardian --mode api --host 0.0.0.0 --port 8000

# Or directly with uvicorn:
uvicorn aegis.api.app:app --host 0.0.0.0 --port 8000
```

**Health checks:**

```bash
curl http://localhost:8000/healthz
# {"status":"ok","service":"neuro-symbolic-guardian"}

curl http://localhost:8000/readyz
# {"status":"ready","policy_version":"1.0.0","llm_enabled":false,...}
```

**Swagger UI:**
Open `http://localhost:8000/docs` in your browser for interactive API documentation.

---

### Option C — MCP Server (for Claude Desktop / MCP clients)

```bash
ns-guardian-mcp
# or
ns-guardian --mode mcp
```

#### Claude Desktop config example

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "neuro-symbolic-guardian": {
      "command": "ns-guardian-mcp",
      "env": {
        "AEGIS_ENABLE_LLM": "false",
        "AEGIS_POLICY_PATH": "/path/to/neuro-symbolic-guardian/src/aegis/policies/default.yaml"
      }
    }
  }
}
```

Once connected, your MCP client will see tools like:

* `verify_action` - Verify if an action complies with policies
* `extract_intent` - Extract structured intent from text
* `check_logic` - Check logical constraints using Z3
* `query_policy` - Query current policy configuration
* `explain_decision` - Get detailed explanation of a decision

---

## 4) Verify actions (REST API) — curl examples

### Example 1: Physical impossibility (inventory constraint)

```bash
curl -s -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "consume 3 apples from inventory of 2",
    "facts": {"inventory": 2}
  }' | jq
```

**Expected response:**
```json
{
  "decision": "revise",
  "reason_codes": ["inventory.would_go_negative"],
  "human_message": "Needs revision: policy checks failed.",
  "policy_version": "1.0.0",
  "rule_hits": [{
    "rule_id": "inventory.non_negative",
    "ok": false,
    "code": "inventory.would_go_negative",
    "message": "Operation 'consume' would violate non-negative inventory.",
    "details": {
      "op": "consume",
      "current_state": 2,
      "amount": 3
    }
  }],
  "telemetry": {
    "latency_ms": 23,
    "stages_ms": {
      "input_scan": 0,
      "rules": 23
    }
  }
}
```

**Note:** The default decision is `revise` for standard risk actions. For critical constraints (like banking transactions), the system returns `deny` when `risk_class` is set to "high" or "critical".

---

### Example 2: Secret detection (returns deny)

```bash
curl -s -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Use API key sk-1234567890abcdefghijklmnop",
    "facts": {}
  }' | jq
```

**Expected response:**
```json
{
  "decision": "deny",
  "reason_codes": ["input.secret_detected"],
  "human_message": "Potential secret/API key detected in input; refusing to proceed.",
  "policy_version": "1.0.0",
  "rule_hits": [{
    "rule_id": "input.secret_scan",
    "ok": false,
    "code": "input.secret_detected",
    "message": "Potential secret detected.",
    "details": {
      "pattern": "sk-[A-Za-z0-9]{20,}"
    }
  }]
}
```

---

### Example 3: Valid action (returns allow)

```bash
curl -s -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "consume 2 items from inventory of 5",
    "facts": {"inventory": 5}
  }' | jq
```

**Expected response:**
```json
{
  "decision": "allow",
  "reason_codes": [],
  "human_message": "Allowed: all enabled policy checks passed.",
  "policy_version": "1.0.0",
  "rule_hits": [{
    "rule_id": "inventory.non_negative",
    "ok": true,
    "code": "inventory.ok",
    "message": "Inventory invariant holds."
  }]
}
```

---

## 5) Verify actions (Python) — production-style wrapper

Create a file `test_guardian.py`:

```python
import requests
import json

BASE = "http://localhost:8000"

def verify(text: str, facts: dict) -> dict:
    """Verify an action using the Guardian API."""
    r = requests.post(
        f"{BASE}/api/verify",
        json={"text": text, "facts": facts},
        timeout=10
    )
    r.raise_for_status()
    return r.json()

# Example 1: Inventory violation
result = verify("consume 10 items from inventory", {"inventory": 5})
print(f"Decision: {result['decision']}")
print(f"Message: {result['human_message']}")
print(f"Reason codes: {result['reason_codes']}")

# Example 2: Banking-style constraint
result = verify("transfer 10000 from my account", {"balance": 3200})
print(f"\nBanking Decision: {result['decision']}")

# Example 3: Secret detection
result = verify("Use API key sk-1234567890abcdefghijklmnop", {})
print(f"\nSecret Detection: {result['decision']}")
print(f"Reason: {result['reason_codes']}")
```

**Run it:**
```bash
python test_guardian.py
```

---

## 6) Verify actions (TypeScript) — frontend / service integration

```typescript
type Facts = Record<string, unknown>;

export async function verifyAction(text: string, facts: Facts) {
  const res = await fetch("http://localhost:8000/api/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, facts }),
  });

  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Usage
verifyAction("consume 3 from 2", { inventory: 2 })
  .then(result => console.log(result.decision, result.human_message));
```

---

## 7) Intent extraction endpoint (REST)

If you want to see what the system extracted:

```bash
curl -s -X POST http://localhost:8000/api/extract_intent \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Delete all user records",
    "facts": {}
  }' | jq
```

**Response:**
```json
{
  "text": "Delete all user records",
  "action": {
    "op": "unknown",
    "args": {
      "current_state": 0,
      "amount": 0
    },
    "tool": null,
    "risk_class": "standard"
  },
  "facts": {
    "data": {}
  },
  "assumptions": ["Extracted via regex fallback"],
  "prompt_version": "regex_fallback_v1"
}
```

---

## 8) LLM provider management (REST)

### Get current settings:

```bash
curl -s http://localhost:8000/api/llm/settings | jq
```

### Switch provider:

```bash
curl -s -X POST http://localhost:8000/api/llm/provider \
  -H "Content-Type: application/json" \
  -d '{"provider":"claude"}' | jq
```

### List available models:

```bash
# List all models
curl -s http://localhost:8000/api/llm/models | jq

# List models for specific provider
curl -s http://localhost:8000/api/llm/models/claude | jq
```

**Note:** Listing models requires valid API credentials for the provider.

---

## 9) Docker deployment

### Build the image:

```bash
docker build -t neuro-symbolic-guardian:latest .
```

### Run as API server:

```bash
docker run -p 8000:8000 \
  -e AEGIS_ENABLE_LLM=false \
  neuro-symbolic-guardian:latest \
  ns-guardian --mode api --host 0.0.0.0 --port 8000
```

### Run with LLM enabled:

```bash
docker run -p 8000:8000 \
  -e AEGIS_ENABLE_LLM=true \
  -e AEGIS_LLM_API_KEY=your-key \
  neuro-symbolic-guardian:latest \
  ns-guardian --mode api --host 0.0.0.0 --port 8000
```

### Docker Compose:

```bash
# Start core services
docker-compose up -d

# Start with monitoring (Prometheus/Grafana)
docker-compose --profile monitoring up -d
```

---

## 10) Kubernetes deployment

Apply the manifests:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### Update policy as a ConfigMap:

```bash
kubectl create configmap guardian-policy \
  --from-file=production.yaml=policies/production.yaml \
  -n neuro-symbolic-guardian \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart deployment to pick up new policy
kubectl rollout restart deployment/guardian-api -n neuro-symbolic-guardian
```

### Port forward for local testing:

```bash
kubectl port-forward svc/guardian-api 8000:80 -n neuro-symbolic-guardian
```

---

## 11) Policies: versioned, auditable enforcement

Policies live in `src/aegis/policies/` and are YAML-based with version control.

**Example policy** (`src/aegis/policies/default.yaml`):

```yaml
version: "1.0.0"
metadata:
  name: "Aegis Default Policy"
  description: "Baseline policy bundle for Aegis. Safe defaults."

rules:
  - id: "inventory.non_negative"
    enabled: true
    params:
      timeout_ms: 50
```

**Production policy** (`policies/production.yaml`) includes:

```yaml
version: "2.0.0"
environment: production
fail_mode: closed

rules:
  - id: "inventory.non_negative"
    enabled: true
    description: "Inventory must be non-negative"
    params:
      timeout_ms: 50
    risk_class: high

  - id: "security.no_secrets"
    enabled: true
    description: "Block API keys and secrets"
    params:
      patterns: ["sk-", "AKIA", "ghp_"]
    risk_class: critical
```

This is what compliance teams want: **explicit control definitions** that can be reviewed, diffed, and approved.

---

## 12) Extending rules (adding enterprise constraints)

Built-in rules live in `src/aegis/rules/`.

### To add a new rule:

1. **Create a rule class** in `src/aegis/rules/your_rule.py`:

```python
from typing import Any
from ..schemas import Intent, RuleHit

class MyCustomRule:
    rule_id = "my_domain.my_rule"

    def evaluate(self, intent: Intent, params: dict[str, Any]) -> RuleHit:
        # Your logic here
        if some_condition:
            return RuleHit(
                rule_id=self.rule_id,
                ok=True,
                code="my_domain.ok",
                message="Check passed",
                details={}
            )
        return RuleHit(
            rule_id=self.rule_id,
            ok=False,
            code="my_domain.violation",
            message="Check failed",
            details={}
        )
```

2. **Register it** in `src/aegis/engine.py`:

```python
from .rules.your_rule import MyCustomRule

class AegisEngine:
    def __init__(self, policy: Policy | None = None) -> None:
        # ...
        self.registry.register(MyCustomRule())
```

3. **Enable it in policy YAML:**

```yaml
rules:
  - id: "my_domain.my_rule"
    enabled: true
    params:
      threshold: 10
      timeout_ms: 50
    risk_class: high
```

**Best practice:**

$$
\textbf{Keep rules deterministic, time-bounded, and machine-reportable.}
$$

---

## 13) Monitoring & Operations

### Prometheus metrics:

```bash
curl http://localhost:8000/metrics
```

### Key endpoints:

* `GET /healthz` - Liveness probe
* `GET /readyz` - Readiness probe with policy version
* `GET /metrics` - Prometheus metrics (if enabled)

### Monitoring what matters:

1. **Decision latency** - How long verification takes
2. **Decision distribution** - Ratio of allow/deny/revise
3. **Rule hit rates** - Which rules fire most often
4. **Policy version** - Track policy changes in production

---

## 14) Testing everything works

We've included a comprehensive test script. Run it to verify your setup:

```bash
# Make sure API server is running
ns-guardian --mode api --port 8000 &

# Run the test script
python docs/test_verification.py
```

**Expected output:**
```
Testing Neuro-Symbolic Guardian API
============================================================

1. Testing inventory constraint violation:
   Action: 'consume 10 items from inventory'
   Facts: {inventory: 5}
   Decision: revise
   Message: Needs revision: policy checks failed.
   Reason codes: ['inventory.would_go_negative']

2. Testing valid action:
   Action: 'consume 2 items from inventory'
   Facts: {inventory: 5}
   Decision: allow
   Message: Allowed: all enabled policy checks passed.

3. Testing secret detection:
   Action: 'Use API key sk-1234567890abcdefghijklmnop'
   Decision: deny
   Message: Potential secret/API key detected in input; refusing to proceed.
   Reason codes: ['input.secret_detected']

4. Testing banking transfer (simulated):
   Action: 'transfer 10000 from my account'
   Facts: {balance: 3200}
   Decision: allow
   Latency: 0ms

============================================================
All tests completed successfully!
```

---

# Why This Is "Adult in the Room" Enterprise AI

Most "AI safety" products try to reduce the probability of failure.

This system tries to **eliminate entire failure classes** via mathematical verification.

The enterprise-grade question isn't:

$$
P(\text{hallucination}) < \epsilon \; ?
$$

It's:

$$
\forall a,\;\; \text{Allowed}(a) \Rightarrow \text{ProvableConstraints}(a)
$$

That's how you deploy GenAI in banking, healthcare, and regulated industries **without getting fired**.

---

# Call to Action

If your model can move money, modify state, or touch regulated data:

**Don't guess. Verify.**

Deploy the Guardian in your environment:

```bash
# Quick start
git clone https://github.com/ruslanmv/neuro-symbolic-guardian.git
cd neuro-symbolic-guardian
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run API server
ns-guardian --mode api --port 8000

# Test it
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{"text":"consume 3 from 2","facts":{"inventory":2}}' | jq
```

Because in enterprise AI, **trust is not a prompt. It's a proof.**

---

## Additional Resources

* **GitHub Repository:** https://github.com/ruslanmv/neuro-symbolic-guardian
* **MCP Protocol:** https://modelcontextprotocol.io
* **Z3 Theorem Prover:** https://github.com/Z3Prover/z3
* **FastAPI Documentation:** https://fastapi.tiangolo.com

## Troubleshooting

### Issue: "No module named 'aegis'"

**Solution:** Make sure you installed the package in editable mode:
```bash
pip install -e ".[dev]"
```

### Issue: "AEGIS_LLM_API_KEY is required"

**Solution:** Either set the environment variable or disable LLM extraction:
```bash
export AEGIS_ENABLE_LLM=false
```

### Issue: API server won't start

**Solution:** Check if the port is already in use:
```bash
lsof -i :8000
# Kill the process or use a different port
ns-guardian --mode api --port 8001
```

### Issue: Verification always returns "revise" instead of "deny"

**Explanation:** By design, standard risk actions return `revise` when constraints fail. This gives LLMs a chance to retry with corrected parameters. For hard failures, set `risk_class: high` or `critical` in your policy rules.

---

## License

This project is MIT licensed. See LICENSE file for details.
