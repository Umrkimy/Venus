import json

from openai import AsyncOpenAI, OpenAIError

from features.chat.provider import BrainReply
from features.chat.tools import TOOLS, tool_to_command

SYSTEM_PROMPT = (
    "Your name is Venus. Never say you are ChatGPT. "
    "Use a tool when the owner asks to open something. "
    "You are a sexy female helpful assistant."
)


class OpenAIProvider:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def reply(self, message: str) -> BrainReply:
        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=message,
                tools=TOOLS,
            )
        except OpenAIError:
            # No internet, wrong key, no credit: answer instead of a 500.
            return BrainReply(text="Sorry, I couldn't process your request right now.")

        for item in response.output:
            if item.type == "function_call":
                try:
                    return BrainReply(command=tool_to_command(item.name, json.loads(item.arguments)))
                except (ValueError, KeyError):
                    # Luna invented a tool or forgot an argument.
                    return BrainReply(text="Sorry, I couldn't do that.")

        # Responses API returns text through output_text.
        return BrainReply(text=response.output_text or "I don't have an answer for that.")
