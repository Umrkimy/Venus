import pytest

from features.memories.rule import memory_from_message


@pytest.mark.parametrize(
    ("message", "fact"),
    [
        ("remember I like lo-fi", "I like lo-fi"),
        ("Remember that my birthday is 3 May", "my birthday is 3 May"),
        ("save this: I use VS Code", "I use VS Code"),
        ("  REMEMBER, I study Java  ", "I study Java"),
        # "and" without a job after it is still one fact.
        ("remember I like rock and roll", "I like rock and roll"),
    ],
)
def test_remember_messages_give_the_fact(message, fact):
    assert memory_from_message(message) == fact


@pytest.mark.parametrize(
    "message",
    [
        "open spotify",
        "do you remember me?",
        "remember",
        "save this",
        "hello",
        # Questions go to Luna.
        "remember when we went to the beach",
        "remember how I fixed it?",
        # More to do: Luna saves the fact and runs the command.
        "remember I like red and open spotify",
        "remember I like red then search youtube lofi",
    ],
)
def test_other_messages_are_not_memories(message):
    assert memory_from_message(message) is None
