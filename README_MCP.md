# Neuro-Symbolic Guardian MCP Server

## Overview

The **Neuro-Symbolic Guardian** is a production-ready Model Context Protocol (MCP) server that provides a symbolic logic layer for Large Language Models. It acts as the "Prefrontal Cortex" for LLMs, ensuring that AI outputs are mathematically verifiable and logically sound.

## Architecture

The Guardian implements a hybrid neuro-symbolic approach:

1. **Neural Component**: Uses LLMs for natural language understanding and intent extraction
2. **Symbolic Component**: Uses Z3 Theorem Prover for formal verification and constraint checking
3. **MCP Interface**: Exposes tools, resources, and prompts for seamless LLM integration

## Installation

### Using UV (Recommended)

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/ruslanmv/neuro-symbolic-guardian.git
cd neuro-symbolic-guardian

# Create virtual environment and install
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install -e ".[dev]"
```

## Usage

### As MCP Server

The Guardian can be used as an MCP server by any MCP-compatible LLM client (Claude Desktop, etc.):

```bash
ns-guardian-mcp
```

### Configuration

Add to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "neuro-symbolic-guardian": {
      "command": "ns-guardian-mcp",
      "env": {
        "AEGIS_ENABLE_LLM": "true",
        "AEGIS_LLM_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Standalone API Server

You can also run the FastAPI server directly:

```bash
uvicorn aegis.api.app:app --host 0.0.0.0 --port 8000
```

## MCP Tools

The Guardian exposes the following tools:

### `verify_action`
Verifies if an action is logically valid and complies with policies.

**Input:**
```json
{
  "text": "consume 3 apples from inventory of 2",
  "facts": {"inventory": 2}
}
```

**Output:**
```json
{
  "decision": "deny",
  "reason_codes": ["inventory.negative_result"],
  "human_message": "Action would violate physical constraints"
}
```

### `extract_intent`
Extracts structured intent from natural language.

**Input:**
```json
{
  "text": "Delete all user records from the database",
  "domain": "database_operations"
}
```

**Output:**
```json
{
  "action": {
    "op": "delete",
    "args": {"target": "user_records", "scope": "all"},
    "risk_class": "critical"
  }
}
```

### `check_logic`
Performs pure logical constraint checking using Z3.

**Input:**
```json
{
  "constraints": ["x > 0", "x < 10", "x > 15"],
  "variables": {"x": "Int"}
}
```

**Output:**
```json
{
  "satisfiable": false,
  "counter_example": "No valid value for x satisfies all constraints"
}
```

### `add_rule`
Adds a new verification rule to the policy.

**Input:**
```json
{
  "rule_id": "database.no_truncate",
  "description": "Prevent table truncation",
  "constraint": "action.op != 'truncate'"
}
```

### `query_policy`
Queries the current policy configuration.

## MCP Resources

The Guardian exposes these resources:

- `policy://current` - Current active policy configuration
- `rules://list` - List of all available rules
- `knowledge://facts` - Current knowledge base facts

## MCP Prompts

Pre-configured prompts for common tasks:

- `generate_constraints` - Generate Z3 constraints from natural language
- `explain_violation` - Explain why an action was blocked
- `suggest_fix` - Suggest how to fix a policy violation

## Examples

### Example 1: Physical Constraint Violation

```python
# User asks: "I have 2 apples, I eat 3"
# Guardian response:
{
  "decision": "deny",
  "reason": "Physical impossibility - cannot consume more items than exist",
  "proof": "inventory(2) AND consume(3) => inventory(-1) [INVALID: inventory >= 0]"
}
```

### Example 2: Security Policy Enforcement

```python
# User asks: "Create an S3 bucket with public access"
# Guardian response:
{
  "decision": "deny",
  "reason": "Security policy violation",
  "rule_violated": "cloud.no_public_buckets",
  "suggestion": "Create bucket with private access, then configure specific permissions"
}
```

### Example 3: Compliance Check

```python
# User asks: "Process credit card data without encryption"
# Guardian response:
{
  "decision": "deny",
  "reason": "Compliance violation: PCI-DSS requires encryption at rest and in transit",
  "regulation": "PCI-DSS 3.4",
  "required_controls": ["encryption_at_rest", "encryption_in_transit"]
}
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ns_guardian --cov=aegis --cov-report=html

# Run specific test file
pytest tests/test_mcp_server.py
```

### Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy src/
```

## Production Deployment

### Docker

```bash
docker build -t neuro-symbolic-guardian:latest .
docker run -p 8000:8000 \
  -e AEGIS_ENABLE_LLM=true \
  -e AEGIS_LLM_API_KEY=your-key \
  neuro-symbolic-guardian:latest
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests.

### Environment Variables

- `AEGIS_ENV` - Environment (dev/staging/prod)
- `AEGIS_POLICY_PATH` - Path to policy YAML
- `AEGIS_ENABLE_LLM` - Enable LLM-based extraction
- `AEGIS_LLM_BASE_URL` - LLM API endpoint
- `AEGIS_LLM_API_KEY` - LLM API key
- `AEGIS_LLM_MODEL` - Model name (default: gpt-4o-mini)
- `AEGIS_LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

## Architecture Details

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
        # Step 4: Generate counter-example and explanation
        return {
            "decision": "deny",
            "reason": explain_violation(result.unsat_core),
            "suggestion": suggest_fix(result.unsat_core)
        }
```

### Policy System

Policies are versioned YAML files that define:

- **Rules**: Logical constraints that must be satisfied
- **Risk Classes**: How to handle failures (fail-open vs fail-closed)
- **Timeouts**: Maximum time for constraint solving
- **Fallbacks**: What to do when verification is uncertain

Example policy:

```yaml
version: "2.0.0"
environment: production
fail_mode: closed  # deny on uncertainty

rules:
  - id: "inventory.non_negative"
    enabled: true
    description: "Inventory cannot go negative"
    params:
      timeout_ms: 50

  - id: "security.no_secrets"
    enabled: true
    description: "Block API keys and secrets"
    params:
      patterns: ["sk-", "AKIA"]

  - id: "compliance.pci_dss"
    enabled: true
    description: "PCI-DSS compliance checks"
    params:
      require_encryption: true
      require_audit_log: true
```

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## License

Apache 2.0 - See LICENSE file for details.

## Citation

If you use this project in research, please cite:

```bibtex
@software{neuro_symbolic_guardian,
  author = {Magana Vsevolodovna, Ruslan},
  title = {Neuro-Symbolic Guardian: MCP Server for LLM Verification},
  year = {2026},
  url = {https://github.com/ruslanmv/neuro-symbolic-guardian}
}
```

## Contact

- Author: Ruslan Magana Vsevolodovna
- GitHub: [@ruslanmv](https://github.com/ruslanmv)
