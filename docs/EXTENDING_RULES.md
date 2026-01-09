# Extending Aegis rules

Aegis treats the verifier as a **policy enforcement layer**: it evaluates versioned policies against a validated `Intent` and returns a standard `AegisDecision`.

## Where rules live
- Built-in rules live under `src/aegis/rules/`
- Policies live under `src/aegis/policies/`

Example built-in Z3 rule:
- `src/aegis/rules/inventory.py` (`inventory.non_negative`)

## Rule interface
Implement a class with:
- `rule_id: str`
- `evaluate(intent, params) -> RuleHit`

See `src/aegis/rules/base.py` for the `Rule` protocol and `RuleHit` schema.

## Registering rules
For now, register rules in `AegisEngine.__init__`:

```python
from aegis.rules.my_rule import MyRule
engine.registry.register(MyRule())
```

(You can later replace this with plugin loading/entry points.)

## Policy wiring
Enable your rule in a policy YAML:

```yaml
version: "1.0.0"
rules:
  - id: "my_rule.id"
    enabled: true
    params:
      threshold: 10
```

## Best practices
- Keep rules deterministic (stable ordering, stable codes/messages)
- Add timeouts to symbolic checks (`solver.set(timeout=...)`)
- Provide machine-readable `code` values for reporting and dashboards
- Unit test each rule (happy path + failure path)
