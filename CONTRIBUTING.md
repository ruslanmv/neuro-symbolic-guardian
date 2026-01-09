# Contributing to Neuro-Symbolic Guardian

Thank you for your interest in contributing to the Neuro-Symbolic Guardian! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue on GitHub with:

1. A clear, descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Environment details (OS, Python version, etc.)
6. Any relevant logs or error messages

### Suggesting Features

We welcome feature suggestions! Please open an issue with:

1. A clear description of the feature
2. The problem it solves
3. Any implementation ideas you have
4. Examples of how it would be used

### Pull Requests

1. **Fork the repository** and create a branch from `main`
2. **Make your changes** following the coding standards below
3. **Add tests** for any new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass** (`make test`)
6. **Run linting and formatting** (`make lint format`)
7. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- Python 3.11 or higher
- UV package manager (recommended)
- Git

### Setup Instructions

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/neuro-symbolic-guardian.git
cd neuro-symbolic-guardian

# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
make install
make dev

# Activate virtual environment
source .venv/bin/activate
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_mcp_server.py -v
```

### Code Quality

```bash
# Format code
make format

# Run linter
make lint

# Type checking
make typecheck
```

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Maximum line length: 120 characters
- Use descriptive variable and function names
- Write docstrings for all public functions and classes

### Example Function

```python
from __future__ import annotations

def verify_constraint(
    constraint: str,
    facts: dict[str, Any],
    timeout_ms: int = 100
) -> tuple[bool, str | None]:
    """Verify a logical constraint using Z3.

    Args:
        constraint: The logical constraint to verify
        facts: Known facts as variable bindings
        timeout_ms: Timeout in milliseconds

    Returns:
        Tuple of (is_satisfiable, error_message)

    Raises:
        ValueError: If constraint syntax is invalid
    """
    # Implementation here
    pass
```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(mcp): add new verify_action tool
fix(engine): handle timeout correctly in Z3 solver
docs(readme): update installation instructions
test(integration): add tests for policy enforcement
```

## Project Structure

```
neuro-symbolic-guardian/
├── src/
│   ├── aegis/              # Core verification engine
│   │   ├── api/           # FastAPI REST server
│   │   ├── extractors/    # Intent extractors
│   │   ├── providers/     # LLM providers
│   │   ├── rules/         # Verification rules
│   │   └── engine.py      # Main engine
│   └── ns_guardian/        # MCP server implementation
│       ├── mcp_server.py  # MCP server
│       └── server.py      # Multi-mode server
├── tests/                  # Test files
├── policies/              # Policy configurations
├── k8s/                   # Kubernetes manifests
├── monitoring/            # Monitoring configs
└── docs/                  # Documentation
```

## Adding New Rules

To add a new verification rule:

1. Create a new file in `src/aegis/rules/`
2. Implement the `Rule` protocol:

```python
from __future__ import annotations

from typing import Any

from ..schemas import Intent, RuleHit


class MyCustomRule:
    """Description of what this rule checks."""

    rule_id = "domain.my_rule"

    def evaluate(
        self,
        intent: Intent,
        params: dict[str, Any]
    ) -> RuleHit:
        """Evaluate the rule against the intent.

        Args:
            intent: The structured intent to verify
            params: Rule parameters from policy

        Returns:
            RuleHit with evaluation results
        """
        # Your logic here
        ok = True  # or False
        code = "domain.my_rule.passed"  # or failure code
        message = "Rule passed"

        return RuleHit(
            rule_id=self.rule_id,
            ok=ok,
            code=code,
            message=message,
            details={}
        )
```

3. Register it in `src/aegis/engine.py`:

```python
def __init__(self, policy: Optional[Policy] = None) -> None:
    # ... existing code ...
    self.registry.register(MyCustomRule())
```

4. Add tests in `tests/test_rules.py`

5. Update policy in `policies/production.yaml`:

```yaml
rules:
  - id: "domain.my_rule"
    enabled: true
    params:
      # your parameters
```

## Adding MCP Tools

To add a new MCP tool:

1. Add tool definition in `src/ns_guardian/mcp_server.py`:

```python
@self.server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools ...
        Tool(
            name="my_tool",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param": {"type": "string", "description": "Parameter description"}
                },
                "required": ["param"]
            }
        )
    ]
```

2. Implement the handler:

```python
@self.server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    if name == "my_tool":
        return await self._my_tool(arguments)
    # ... existing handlers ...

async def _my_tool(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
    # Implementation
    result = {"key": "value"}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

3. Add tests in `tests/test_mcp_server.py`

## Documentation

- Update README.md for user-facing changes
- Update README_MCP.md for MCP-specific features
- Add docstrings to all new code
- Update policy examples if adding new rules
- Add inline comments for complex logic

## Testing Guidelines

### Unit Tests

- Test individual functions and classes
- Mock external dependencies
- Use pytest fixtures for common setup
- Aim for high coverage (>80%)

### Integration Tests

- Test complete workflows
- Test with real Z3 solver
- Test policy loading and validation
- Test error handling

### Example Test

```python
import pytest
from aegis.engine import AegisEngine
from aegis.schemas import Decision


def test_physical_constraint_violation():
    """Test that physical constraints are enforced."""
    engine = AegisEngine()
    intent = create_test_intent("consume 3 from 2", {"inventory": 2})

    decision = engine.verify(intent)

    assert decision.decision == Decision.deny
    assert "inventory" in str(decision.reason_codes)
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create PR to main branch
5. After merge, tag release: `git tag -a v2.0.1 -m "Release v2.0.1"`
6. Push tag: `git push origin v2.0.1`

## Getting Help

- Check existing issues and discussions
- Ask questions in GitHub Discussions
- Review documentation in `docs/`
- Contact maintainers: [@ruslanmv](https://github.com/ruslanmv)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

## Recognition

Contributors will be acknowledged in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to making AI safer and more reliable! 🎉
