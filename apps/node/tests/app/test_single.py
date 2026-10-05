from uuid import uuid4

from venus_node.app.single import already_running_message, ask_to_quit, claim, quit_signal, wait_for_quit


def test_claim_lets_only_the_first_holder_run():
    name = rf"Local\VenusTest-{uuid4().hex}"

    assert claim(name) is True
    assert claim(name) is False


def test_claim_names_are_independent():
    assert claim(rf"Local\VenusTest-{uuid4().hex}") is True
    assert claim(rf"Local\VenusTest-{uuid4().hex}") is True


def test_already_running_message_says_what_to_do():
    assert already_running_message("Listening") == (
        "Listening is already running (Venus tray app or another window). Quit it first."
    )


def test_ask_to_quit_reaches_the_running_app():
    name = rf"Local\VenusTest-{uuid4().hex}"
    assert ask_to_quit(name) is False  # Nothing running yet.

    signal = quit_signal(name)
    assert ask_to_quit(name) is True
    wait_for_quit(signal)  # Returns at once: the quit arrived.

