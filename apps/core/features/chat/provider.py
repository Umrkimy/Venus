from typing import Protocol


class ChatProvider(Protocol):
    async def reply(self, message: str) -> str: ...


class FakeProvider:
    async def reply(self, message: str) -> str:
        return f"Fake Venus: {message}"
