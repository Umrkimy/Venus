import asyncio
from types import SimpleNamespace

from openai import OpenAIError

from features.chat.openai_provider import SYSTEM_PROMPT, OpenAIProvider


class FakeCompletions:
    def __init__(self, error: Exception | None = None, content: str | None = "Hi from Luna"):
        self.calls = []
        self.error = error
        self.content = content

    async def create(self, **kwargs):
        # Remember what the provider sent, then answer like the SDK would.
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=FakeCompletions(**kwargs))


def test_openai_provider_returns_model_text():
    provider = OpenAIProvider(FakeClient(), "gpt-6-luna")

    assert asyncio.run(provider.reply("hello")) == "Hi from Luna"


def test_openai_provider_sends_model_system_prompt_and_message():
    client = FakeClient()
    provider = OpenAIProvider(client, "gpt-6-luna")

    asyncio.run(provider.reply("hello"))

    assert client.chat.completions.calls == [
        {
            "model": "gpt-6-luna",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "hello"},
            ],
        },
    ]


def test_openai_provider_turns_api_errors_into_friendly_reply():
    provider = OpenAIProvider(FakeClient(error=OpenAIError("boom")), "gpt-6-luna")

    reply = asyncio.run(provider.reply("hello"))

    assert reply
    assert "boom" not in reply


def test_openai_provider_never_returns_empty_text():
    # The SDK's content is None when the model answers without text.
    provider = OpenAIProvider(FakeClient(content=None), "gpt-6-luna")

    reply = asyncio.run(provider.reply("hello"))

    assert isinstance(reply, str)
    assert reply
