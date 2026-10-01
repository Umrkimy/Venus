import asyncio
from types import SimpleNamespace

import pytest
from openai import OpenAIError

from features.chat.openai_provider import SYSTEM_PROMPT, OpenAIProvider
from features.chat.provider import BrainReply
from features.chat.tools import TOOLS


def function_call(name: str, arguments: str):
    return SimpleNamespace(type="function_call", name=name, arguments=arguments)


class FakeResponses:
    def __init__(
        self,
        error: Exception | None = None,
        output: list | None = None,
        output_text: str = "Hi from Luna",
    ):
        self.calls = []
        self.error = error
        self.output = output or []
        self.output_text = output_text

    async def create(self, **kwargs):
        # Remember what the provider sent, then answer like the SDK would.
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output=self.output, output_text=self.output_text)


class FakeClient:
    def __init__(self, **kwargs):
        self.responses = FakeResponses(**kwargs)


def test_openai_provider_returns_model_text():
    provider = OpenAIProvider(FakeClient(), "gpt-6-luna")

    assert asyncio.run(provider.reply("hello")) == BrainReply(text="Hi from Luna")


def test_openai_provider_sends_model_instructions_message_and_tools():
    client = FakeClient()
    provider = OpenAIProvider(client, "gpt-6-luna")

    asyncio.run(provider.reply("hello"))

    assert client.responses.calls == [
        {
            "model": "gpt-6-luna",
            "instructions": SYSTEM_PROMPT,
            "input": "hello",
            "tools": TOOLS,
        },
    ]


def test_openai_provider_turns_function_call_into_command():
    client = FakeClient(
        output=[function_call("open_app", '{"name": "Spotify"}')],
        output_text="",
    )
    provider = OpenAIProvider(client, "gpt-6-luna")

    assert asyncio.run(provider.reply("can you open spotify")) == BrainReply(
        command="open Spotify",
    )


@pytest.mark.parametrize(
    "item",
    [
        function_call("delete_files", '{"path": "C:/"}'),  # invented tool
        function_call("open_app", "{}"),  # missing argument
        function_call("open_app", "not json"),  # broken arguments
    ],
)
def test_openai_provider_answers_when_function_call_is_broken(item):
    provider = OpenAIProvider(FakeClient(output=[item]), "gpt-6-luna")

    reply = asyncio.run(provider.reply("do something"))

    assert reply.command is None
    assert reply.text


def test_openai_provider_turns_api_errors_into_friendly_reply():
    provider = OpenAIProvider(FakeClient(error=OpenAIError("boom")), "gpt-6-luna")

    reply = asyncio.run(provider.reply("hello"))

    assert reply.text
    assert "boom" not in reply.text


def test_openai_provider_never_returns_empty_text():
    # output_text is "" when the model answers without text.
    provider = OpenAIProvider(FakeClient(output_text=""), "gpt-6-luna")

    reply = asyncio.run(provider.reply("hello"))

    assert reply.text
