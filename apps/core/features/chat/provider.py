from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BrainReply:
    text: str | None = None      # Luna answered with words
    command: str | None = None   # Luna chose a tool, written as parser text


class ChatProvider(Protocol):
    async def reply(self, message: str) -> BrainReply: ...


class FakeProvider:
    async def reply(self, message: str) -> BrainReply:
        return BrainReply(text=f"Fake Venus: {message}")
