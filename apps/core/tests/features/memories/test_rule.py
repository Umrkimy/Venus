import pytest

from features.memories.rule import memory_from_message


@pytest.mark.parametrize(
    ("message", "fact"),
    [
        ("remember I like lo-fi", "I like lo-fi"),
        ("Remember that my birthday is 3 May", "my birthday is 3 May"),
        ("save this: I use VS Code", "I use VS Code"),
        ("  REMEMBER, I study Java  ", "I study Java"),
    ],
)
def test_remember_messages_give_the_fact(message, fact):
    assert memory_from_message(message) == fact


@pytest.mark.parametrize(
    "message",
    ["open spotify", "do you remember me?", "remember", "save this", "hello"],
)
def test_other_messages_are_not_memories(message):
    assert memory_from_message(message) is None
