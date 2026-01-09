from ns_guardian.llm_interface import LLMInterface


def test_parse_consume():
    llm = LLMInterface()
    intent = llm.parse_user_intent("I have 2 apples. I want to eat 3.")
    assert intent is not None
    assert intent.current_state == 2
    assert intent.action_value == 3
    assert intent.operation == "consume"


def test_parse_add():
    llm = LLMInterface()
    intent = llm.parse_user_intent("I have 2 apples. I want to add 5.")
    assert intent is not None
    assert intent.operation == "add"
