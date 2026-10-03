from collections.abc import Callable

# chat(message, conversation_id) -> Core's answer
ChatCall = Callable[[str, str | None], dict]


class VoiceChat:
    """One chat per listen run: later wakes continue it, so Luna remembers."""

    def __init__(self, chat: ChatCall) -> None:
        self._chat = chat
        self.conversation_id: str | None = None

    def ask(self, message: str) -> str:
        answer = self._chat(message, self.conversation_id)
        # Core makes the chat on the first message and sends its id back.
        self.conversation_id = answer["conversation_id"]
        return answer.get("reply") or ""
