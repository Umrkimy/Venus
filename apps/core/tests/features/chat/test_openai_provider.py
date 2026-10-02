import asyncio
from types import SimpleNamespace

import pytest
from openai import OpenAIError

from features.chat.openai_provider import OpenAIProvider
from features.chat.provider import BrainReply
from features.chat.schemas import ChatTurn
from features.chat.tools import TOOLS


def function_call(name: str, arguments: str):
    return SimpleNamespace(
        type="function_call", name=name, arguments=arguments, call_id="call-1",
    )


class FakeResponses:
    def __init__(
        self,
        error: Exception | None = None,
        output: list | None = None,
        output_text: str = "Hi from Luna",
        followup_error: Exception | None = None,
    ):
        self.calls = []
        self.error = error
        self.output = output or []
        self.output_text = output_text
        self.followup_error = followup_error

    async def create(self, **kwargs):
        # Remember what the provider sent, then answer like the SDK would.
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        if "previous_response_id" in kwargs:
            # Second call after a tool result: answer with words only.
            if self.followup_error is not None:
                raise self.followup_error
            return SimpleNamespace(id="resp-2", output=[], output_text="Love that, Umar!")
        return SimpleNamespace(id="resp-1", output=self.output, output_text=self.output_text)


class FakeClient:
    def __init__(self, **kwargs):
        self.responses = FakeResponses(**kwargs)


def test_openai_provider_returns_model_text():
    provider = OpenAIProvider(FakeClient(), "gpt-6-luna")

    assert asyncio.run(provider.reply("hello", [], "")) == BrainReply(text="Hi from Luna")


def test_openai_provider_sends_model_instructions_message_and_tools():
    client = FakeClient()
    provider = OpenAIProvider(client, "gpt-6-luna")

    asyncio.run(provider.reply("hello", [], "Be Venus."))

    assert client.responses.calls == [
        {
            "model": "gpt-6-luna",
            "instructions": "Be Venus.",
            "input": [{"role": "user", "content": "hello"}],
            "tools": TOOLS,
        },
    ]


def test_openai_provider_sends_history_before_new_message():
    client = FakeClient()
    provider = OpenAIProvider(client, "gpt-6-luna")
    history = [
        ChatTurn(role="user", content="my name is Umar"),
        ChatTurn(role="assistant", content="Nice to meet you, Umar"),
    ]

    asyncio.run(provider.reply("what is my name?", history, ""))

    assert client.responses.calls[0]["input"] == [
        {"role": "user", "content": "my name is Umar"},
        {"role": "assistant", "content": "Nice to meet you, Umar"},
        {"role": "user", "content": "what is my name?"},
    ]


def test_openai_provider_turns_function_call_into_command():
    client = FakeClient(
        output=[function_call("open_app", '{"name": "Spotify"}')],
        output_text="",
    )
    provider = OpenAIProvider(client, "gpt-6-luna")

    assert asyncio.run(provider.reply("can you open spotify", [], "")) == BrainReply(
        command="open Spotify",
    )


def test_openai_provider_saves_memory_and_still_answers():
    client = FakeClient(
        output=[function_call("save_memory", '{"fact": "Owner likes lo-fi"}')],
        output_text="",
    )
    provider = OpenAIProvider(client, "gpt-6-luna")

    reply = asyncio.run(provider.reply("i love lo-fi", [], ""))

    assert reply == BrainReply(text="Love that, Umar!", memory="Owner likes lo-fi")
    followup = client.responses.calls[1]
    assert followup["previous_response_id"] == "resp-1"
    assert followup["input"] == [
        {"type": "function_call_output", "call_id": "call-1", "output": "Saved."},
    ]
    # Luna can't chain another tool from the follow-up answer.
    assert followup["tool_choice"] == "none"


def test_openai_provider_keeps_memory_when_followup_fails():
    client = FakeClient(
        output=[function_call("save_memory", '{"fact": "Owner likes lo-fi"}')],
        output_text="",
        followup_error=OpenAIError("boom"),
    )
    provider = OpenAIProvider(client, "gpt-6-luna")

    reply = asyncio.run(provider.reply("i love lo-fi", [], ""))

    assert reply == BrainReply(memory="Owner likes lo-fi")


@pytest.mark.parametrize(
    "item",
    [
        function_call("delete_files", '{"path": "C:/"}'),  # invented tool
        function_call("open_app", "{}"),  # missing argument
        function_call("open_app", "not json"),  # broken arguments
        function_call("save_memory", "{}"),  # fact missing
    ],
)
def test_openai_provider_answers_when_function_call_is_broken(item):
    provider = OpenAIProvider(FakeClient(output=[item]), "gpt-6-luna")

    reply = asyncio.run(provider.reply("do something", [], ""))

    assert reply.command is None
    assert reply.memory is None
    assert reply.text


def test_openai_provider_turns_api_errors_into_friendly_reply():
    provider = OpenAIProvider(FakeClient(error=OpenAIError("boom")), "gpt-6-luna")

    reply = asyncio.run(provider.reply("hello", [], ""))

    assert reply.text
    assert "boom" not in reply.text


def test_openai_provider_never_returns_empty_text():
    # output_text is "" when the model answers without text.
    provider = OpenAIProvider(FakeClient(output_text=""), "gpt-6-luna")

    reply = asyncio.run(provider.reply("hello", [], ""))

    assert reply.text


def test_openai_provider_say_sends_no_tools():
    client = FakeClient()
    provider = OpenAIProvider(client, "gpt-6-luna")

    line = asyncio.run(provider.say("open spotify", "Be Venus. You opened Spotify."))

    assert line == "Hi from Luna"
    assert "tools" not in client.responses.calls[0]
    assert client.responses.calls[0]["instructions"] == "Be Venus. You opened Spotify."


def test_openai_provider_say_gives_nothing_on_api_error():
    provider = OpenAIProvider(FakeClient(error=OpenAIError("boom")), "gpt-6-luna")

    assert asyncio.run(provider.say("open spotify", "")) is None
