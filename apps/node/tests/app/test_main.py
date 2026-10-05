import sys

import venus_node.app.main as app_main


def fake_start(monkeypatch, claimed: bool):
    events = []
    monkeypatch.setattr(app_main, "claim", lambda name: claimed)
    monkeypatch.setattr(app_main, "log_to_file", lambda path: events.append("log"))
    monkeypatch.setattr(app_main, "show_message", lambda text: events.append(f"popup {text}"))
    monkeypatch.setattr(app_main, "run_app", lambda directory: events.append("run"))
    return events


def test_second_hidden_start_keeps_the_running_log_and_shows_a_popup(monkeypatch):
    events = fake_start(monkeypatch, claimed=False)
    monkeypatch.setattr(sys, "stdout", None)

    app_main.main()

    assert len(events) == 1
    assert events[0].startswith("popup Venus is already running")


def test_second_console_start_prints_instead(monkeypatch, capsys):
    events = fake_start(monkeypatch, claimed=False)

    app_main.main()

    assert events == []
    assert "Venus is already running" in capsys.readouterr().out


def test_first_hidden_start_logs_to_file_then_runs(monkeypatch):
    events = fake_start(monkeypatch, claimed=True)
    monkeypatch.setattr(sys, "stdout", None)

    app_main.main()

    assert events == ["log", "run"]
