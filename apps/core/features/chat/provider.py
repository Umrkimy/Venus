from dataclasses import dataclass
from typing import Protocol

from features.chat.schemas import ChatTurn


@dataclass(frozen=True)
class BrainReply:
    text: str | None = None      # Luna answered with words
    command: str | None = None   # Luna chose a tool, written as parser text
    memory: str | None = None    # Luna wants to remember a fact about the owner


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
