from ns_guardian.guardian import LogicGuardian



def test_valid_consume():
    g = LogicGuardian()
    r = g.verify_transaction(current_state=2, action_value=1, operation="consume")
    assert r.ok is True



def test_invalid_consume():
    g = LogicGuardian()
    r = g.verify_transaction(current_state=2, action_value=3, operation="consume")
    assert r.ok is False
    assert "violates" in r.message or "Failed" in r.message



def test_add_is_always_valid_for_non_negative_amount():
    g = LogicGuardian()
    r = g.verify_transaction(current_state=0, action_value=5, operation="add")
    assert r.ok is True
