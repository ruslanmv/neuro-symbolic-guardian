from aegis.engine import AegisEngine
from aegis.schemas import Action, Intent


def test_aegis_allows_valid_inventory_action():
    engine = AegisEngine()
    intent = Intent(text="consume 1 from 2", action=Action(op="consume", args={"current_state": 2, "amount": 1}))
    decision = engine.verify(intent)
    assert decision.decision.value == "allow"


def test_aegis_revises_invalid_inventory_action():
    engine = AegisEngine()
    intent = Intent(text="consume 3 from 2", action=Action(op="consume", args={"current_state": 2, "amount": 3}))
    decision = engine.verify(intent)
    assert decision.decision.value in {"revise", "deny"}
    assert any("inventory" in c for c in decision.reason_codes)
