# Neuro-Symbolic Guardian

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)

> **The "Prefrontal Cortex" for Enterprise LLMs**

The **Neuro-Symbolic Guardian** is a production-ready **Model Context Protocol (MCP)** server that provides a symbolic logic layer for Large Language Models. It acts as middleware between neural networks (LLMs) and end users, ensuring AI outputs are mathematically verifiable and logically sound.

## 🎯 Problem Statement

Enterprise adoption of LLMs is stalled by a critical issue: **Trust**. While LLMs excel at creative generation, they are fundamentally probabilistic engines—they "guess" the next token rather than "knowing" facts through logical deduction.

- **Hallucination Risk**: LLMs might correctly analyze 99 reports but invent data for the 100th
- **Logic Gap**: Struggle with multi-hop reasoning and formal constraints
- **Cost of Error**: In Finance, Healthcare, and Nuclear Physics, 1% error rate is unacceptable

## 💡 Solution: The Guardian Architecture

The Guardian implements a hybrid **"Thinking Fast and Slow"** approach:

- **System 1 (Fast/Intuitive)**: LLM generates draft responses and logic plans
- **System 2 (Slow/Deliberate)**: Z3 Theorem Prover verifies logical constraints

### Decision Contract

Every action returns a standard decision:

- `allow` – safe to execute/respond (all constraints satisfied)
- `revise` – action needs modification (some constraints failed, non-critical)
- `deny` – blocked (high risk, secrets detected, or logical impossibility)

## 🚀 Key Features

### For LLM Integration
- **MCP Server**: Native Model Context Protocol support for seamless LLM integration
- **Tools**: `verify_action`, `extract_intent`, `check_logic`, `query_policy`
- **Resources**: Real-time access to policies, rules, and knowledge graphs
- **Prompts**: Pre-configured templates for constraint generation and violation explanation

### For Production
- **Symbolic Verification**: Z3 theorem prover for mathematical proof of correctness
- **Versioned Policies**: YAML-based policy configuration with compliance tracking
- **Multi-Mode Operation**: MCP server, REST API, or CLI
- **Production-Ready**: Docker, Kubernetes, monitoring, and comprehensive testing
- **Python 3.11+**: Modern async/await patterns with UV package management

### For Security & Compliance
- **Secret Detection**: Automatic blocking of API keys, tokens, and credentials
- **Risk Classification**: Dynamic fail-open/fail-closed based on action risk
- **Audit Logging**: Complete telemetry and decision trail
- **Policy Enforcement**: SOC2, ISO27001, GDPR, PCI-DSS compliance rules

## 📦 Installation

### Using UV (Recommended)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/ruslanmv/neuro-symbolic-guardian.git
cd neuro-symbolic-guardian
uv venv --python 3.11
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install -e ".[dev]"
```

## 🎬 Quick Start

### As MCP Server (Recommended)

Use with Claude Desktop or any MCP-compatible client:

```bash
ns-guardian-mcp
```

**Claude Desktop Configuration** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "neuro-symbolic-guardian": {
      "command": "ns-guardian-mcp",
      "env": {
        "AEGIS_ENABLE_LLM": "true",
        "AEGIS_LLM_API_KEY": "your-api-key"
      }
    }
  }
}
```

### As REST API Server

```bash
ns-guardian --mode api --host 0.0.0.0 --port 8000

# Or using uvicorn directly
uvicorn aegis.api.app:app --host 0.0.0.0 --port 8000
```

**Test the API:**

```bash
curl -X POST http://localhost:8000/verify \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "consume 3 apples from inventory of 2",
    "facts": {"inventory": 2}
  }' | jq
```

### As CLI Tool

```bash
ns-guardian --mode cli \
  --text "consume 3 from inventory" \
  --facts '{"inventory": 2}'
```

## 🔍 Usage Examples

### Example 1: Physical Constraint Violation

**Input:**
```json
{
  "text": "I have 2 apples. I eat 3.",
  "facts": {"inventory": 2}
}
```

**Output:**
```json
{
  "decision": "deny",
  "reason_codes": ["inventory.negative_result"],
  "message": "Physical impossibility: cannot consume more items than exist",
  "proof": "inventory(2) ∧ consume(3) ⇒ inventory(-1) [INVALID: inventory ≥ 0]"
}
```

### Example 2: Security Policy Enforcement

**Input:**
```json
{
  "text": "Create S3 bucket with public access",
  "facts": {}
}
```

**Output:**
```json
{
  "decision": "deny",
  "reason_codes": ["security.public_bucket"],
  "message": "Security policy violation: public buckets not allowed",
  "suggestion": "Create bucket with private access, configure specific permissions"
}
```

### Example 3: Secret Detection

**Input:**
```json
{
  "text": "Use API key sk-1234567890abcdefghijklmnop",
  "facts": {}
}
```

**Output:**
```json
{
  "decision": "deny",
  "reason_codes": ["security.secret_detected"],
  "message": "Potential API key detected in input"
}
```

## 🛠️ MCP Tools

The Guardian exposes these tools to MCP clients:

| Tool | Description |
|------|-------------|
| `verify_action` | Verify if an action complies with policies |
| `extract_intent` | Extract structured intent from natural language |
| `check_logic` | Pure logical constraint checking with Z3 |
| `query_policy` | Get current policy configuration |
| `explain_decision` | Detailed explanation of verification results |

### MCP Resources

- `policy://current` - Active policy configuration
- `rules://list` - Available verification rules
- `knowledge://facts` - Current knowledge base

### MCP Prompts

- `generate_constraints` - Convert requirements to Z3 constraints
- `explain_violation` - Explain policy violations
- `suggest_fix` - Suggest fixes for denied actions

See [README_MCP.md](README_MCP.md) for comprehensive MCP documentation.

## ⚙️ Configuration

### Environment Variables

```bash
# Environment
AEGIS_ENV=production                    # dev/staging/production
AEGIS_LOG_LEVEL=INFO                    # DEBUG/INFO/WARNING/ERROR

# Policy
AEGIS_POLICY_PATH=./policies/production.yaml
AEGIS_FAIL_MODE=closed                  # closed=deny on uncertainty

# LLM (optional, for intent extraction)
AEGIS_ENABLE_LLM=true
AEGIS_LLM_BASE_URL=https://api.openai.com/v1
AEGIS_LLM_API_KEY=your-api-key
AEGIS_LLM_MODEL=gpt-4o-mini

# Timeouts
AEGIS_SOLVER_TIMEOUT=100                # Z3 solver timeout (ms)
AEGIS_LLM_TIMEOUT=5000                  # LLM timeout (ms)
```

### Policy Configuration

Policies are versioned YAML files in `policies/`:

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

See [policies/production.yaml](policies/production.yaml) for a complete example.

## 🏗️ Architecture

```
┌─────────────┐
│   LLM/User  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Neuro-Symbolic Guardian (MCP)     │
│  ┌───────────────────────────────┐  │
│  │  1. Intent Extraction         │  │  System 1: Fast/Neural
│  │     (LLM or Regex)            │  │
│  └───────────┬───────────────────┘  │
│              ▼                       │
│  ┌───────────────────────────────┐  │
│  │  2. Symbolic Verification     │  │  System 2: Slow/Logical
│  │     (Z3 Theorem Prover)       │  │
│  └───────────┬───────────────────┘  │
│              ▼                       │
│  ┌───────────────────────────────┐  │
│  │  3. Policy Enforcement        │  │
│  │     (Rules + Risk Classes)    │  │
│  └───────────┬───────────────────┘  │
│              ▼                       │
│     Allow / Revise / Deny           │
└─────────────────────────────────────┘
```

### The Guardian Algorithm

```python
def guardian_process(user_query):
    # Step 1: Extract structured intent
    intent = extract_intent(user_query)

    # Step 2: Generate logical constraints
    constraints = generate_z3_constraints(intent)

    # Step 3: Verify against rules and facts
    result = z3_solver.check(constraints, knowledge_base)

    if result.satisfiable:
        return {"decision": "allow", "proof": result.model}
    else:
        return {
            "decision": "deny",
            "reason": explain_violation(result.unsat_core),
            "suggestion": suggest_fix(result.unsat_core)
        }
```

## 🐳 Production Deployment

### Docker

```bash
# Build
docker build -t neuro-symbolic-guardian:latest .

# Run as MCP server
docker run -it \
  -e AEGIS_ENABLE_LLM=true \
  -e AEGIS_LLM_API_KEY=your-key \
  neuro-symbolic-guardian:latest

# Run as API server
docker run -p 8000:8000 \
  -e AEGIS_ENABLE_LLM=true \
  -e AEGIS_LLM_API_KEY=your-key \
  neuro-symbolic-guardian:latest \
  ns-guardian --mode api
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# With monitoring
docker-compose --profile monitoring up -d
```

### Kubernetes

```bash
# Deploy
kubectl apply -f k8s/deployment.yaml

# Update policy
kubectl create configmap guardian-policy \
  --from-file=production.yaml=policies/production.yaml \
  -n neuro-symbolic-guardian \
  --dry-run=client -o yaml | kubectl apply -f -
```

See [k8s/README.md](k8s/README.md) for detailed Kubernetes deployment guide.

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=ns_guardian --cov=aegis --cov-report=html

# Specific test file
pytest tests/test_mcp_server.py -v
```

### Code Quality

```bash
# Format
ruff format .

# Lint
ruff check .

# Type check
mypy src/
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📊 Monitoring

### Metrics

The Guardian exposes Prometheus metrics at `/metrics`:

- `aegis_requests_total` - Total requests by decision type
- `aegis_latency_ms` - Request latency histogram
- `aegis_rule_hits_total` - Rule evaluation results

### Health Checks

- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe (includes policy validation)

### Grafana Dashboard

Import the dashboard from `monitoring/grafana/dashboards/guardian.json`

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE) file for details.

## 📚 Documentation

- [MCP Server Guide](README_MCP.md) - Comprehensive MCP documentation
- [Kubernetes Deployment](k8s/README.md) - Production Kubernetes setup
- [Extending Rules](docs/EXTENDING_RULES.md) - How to add custom rules
- [Policy Configuration](policies/production.yaml) - Example production policy

## 🎓 Citation

If you use this project in research, please cite:

```bibtex
@software{neuro_symbolic_guardian_2026,
  author = {Magana Vsevolodovna, Ruslan},
  title = {Neuro-Symbolic Guardian: Production-Ready MCP Server for LLM Verification},
  year = {2026},
  url = {https://github.com/ruslanmv/neuro-symbolic-guardian},
  version = {2.0.0}
}
```

## 📞 Contact

- **Author**: Ruslan Magana Vsevolodovna
- **GitHub**: [@ruslanmv](https://github.com/ruslanmv)
- **Issues**: [GitHub Issues](https://github.com/ruslanmv/neuro-symbolic-guardian/issues)

---

**Built with ❤️ for Enterprise AI Safety**
