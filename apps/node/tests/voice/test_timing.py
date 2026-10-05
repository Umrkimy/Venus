from venus_node.voice.timing import Timer


def test_timer_reports_seconds_per_step():
    ticks = iter([10.0, 11.25, 14.0])
    timer = Timer(clock=lambda: next(ticks))

    timer.lap("transcribe")
    timer.lap("chat")

    assert timer.report() == "Timing: transcribe 1.2 s, chat 2.8 s"
