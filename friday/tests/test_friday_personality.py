from datetime import datetime

from core.personality import friday_personality


def test_startup_greeting_periods():
    assert friday_personality.startup_greeting(datetime(2026, 4, 25, 8, 0)).message == "Good morning, Boss. Ready to get things done?"
    assert friday_personality.startup_greeting(datetime(2026, 4, 25, 19, 0)).message == "Good evening, Boss. What are we working on today?"
    assert friday_personality.startup_greeting(datetime(2026, 4, 25, 14, 0)).message == "Hello Boss."


def test_interrupt_detection_and_stop_copy():
    assert friday_personality.detect_interruption("stop")
    assert friday_personality.detect_interruption("hold on")
    assert not friday_personality.detect_interruption("stop docker")
    assert friday_personality.stopping_response() == "Alright, stopping that."
