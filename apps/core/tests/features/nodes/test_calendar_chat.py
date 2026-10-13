"""'Add gym tomorrow at 6': Luna's add_calendar_event lands on the Venus calendar."""

from datetime import datetime, timezone

import pytest
from fastapi import status

from features.calendar.dependencies import get_calendar_repository
from features.chat.dependencies import get_chat_provider
from features.chat.provider import BrainReply
from features.chat.schemas import ChatTurn
from features.settings.dependencies import get_settings_repository
from main import app
from tests.features.nodes.test_nodes_router import (  # noqa: F401  (fixtures)
    TEST_OWNER_TOKEN,
    client,
    command_records,
    connected_pc_umar,
    override_node_settings,
)

OWNER = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}


class CalendarBrain:
    def __init__(self, events: list[dict], text: str | None = "Done, it's in your calendar.") -> None:
        self.events = events
        self.text = text

    async def reply(self, message: str, history: list[ChatTurn], instructions: str) -> BrainReply:
        return BrainReply(text=self.text, events=self.events)

    async def say(self, message: str, instructions: str) -> str | None:
        return None


@pytest.fixture(autouse=True)
def kuala_lumpur(override_node_settings):  # noqa: F811
    app.dependency_overrides[get_settings_repository]().set_time("Asia/Kuala_Lumpur", "Malaysia")


def chat(text: str) -> dict:
    response = client.post("/nodes/PC-Umar/chat", json={"message": text}, headers=OWNER)
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()


def venus_events():
    repository = app.dependency_overrides[get_calendar_repository]()
    return repository.venus_events(datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2027, 1, 1, tzinfo=timezone.utc))


def test_luna_adds_an_event_in_the_owners_time():
    app.dependency_overrides[get_chat_provider] = lambda: CalendarBrain(
        [{"title": "Gym", "start": "2026-10-15T18:00", "location": "Uni gym"}],
    )

    with connected_pc_umar():
        body = chat("add gym tomorrow at 6pm")

    assert body["type"] == "reply"
    assert body["reply"] == "Done, it's in your calendar."
    assert body["actions"] == [{"kind": "event", "text": "Gym, Thu 15 Oct, 18:00 @ Uni gym"}]
    [event] = venus_events()
    # 18:00 in Kuala Lumpur is 10:00 UTC; one hour when no end is given.
    assert event.start.replace(tzinfo=timezone.utc) == datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
    assert (event.end - event.start).total_seconds() == 3600
    assert event.location == "Uni gym"


def test_all_day_event():
    app.dependency_overrides[get_chat_provider] = lambda: CalendarBrain([{"title": "Exam", "start": "2026-11-02"}])

    with connected_pc_umar():
        body = chat("put my exam on 2 november")

    [event] = venus_events()
    assert event.all_day is True
    assert body["actions"] == [{"kind": "event", "text": "Exam, Mon 02 Nov"}]


def test_a_bad_time_from_luna_is_an_answer_not_a_crash():
    app.dependency_overrides[get_chat_provider] = lambda: CalendarBrain([{"title": "Gym", "start": "tomorrow-ish"}], text=None)

    with connected_pc_umar():
        body = chat("add gym sometime")

    assert body["type"] == "reply"
    assert "couldn't add that to your calendar" in body["reply"]
    assert venus_events() == []
