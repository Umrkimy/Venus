from dataclasses import dataclass, field
from typing import Protocol

from features.chat.schemas import ChatTurn


@dataclass(frozen=True)
class BrainReply:
    text: str | None = None  # Luna answered with words
    # Tools Luna chose, written as parser text, in the order she asked.
    commands: list[str] = field(default_factory=list)
    # Facts about the owner Luna wants to remember.
    memories: list[str] = field(default_factory=list)


class ChatProvider(Protocol):
    async def reply(
        self, message: str, history: list[ChatTurn], instructions: str,
    ) -> BrainReply: ...

    async def say(self, message: str, instructions: str) -> str | None: ...


class FakeProvider:
    async def reply(
        self, message: str, history: list[ChatTurn], instructions: str,
    ) -> BrainReply:
        return BrainReply(text=f"Fake Venus: {message}")

    async def say(self, message: str, instructions: str) -> str | None:
        # No AI to word it; Core uses its own plain line.
        return None
