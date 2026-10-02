import json

from openai import AsyncOpenAI, OpenAIError

from features.chat.prompt import plain_punctuation
from features.chat.provider import BrainReply
from features.chat.schemas import ChatTurn
from features.chat.tools import TOOLS, tool_to_command

class OpenAIProvider:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def reply(
        self, message: str, history: list[ChatTurn], instructions: str,
    ) -> BrainReply:
        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=[
                    {"role": turn.role, "content": turn.content} for turn in history
                ] + [{"role": "user", "content": message}],
                tools=TOOLS,
            )
        except OpenAIError:
            # No internet, wrong key, no credit: answer instead of a 500.
            return BrainReply(text="Sorry, I couldn't process your request right now.")

        for item in response.output:
            if item.type == "function_call":
                try:
                    arguments = json.loads(item.arguments)
                    if item.name == "save_memory":
                        # Saved by Core itself; nothing goes to the PC.
                        fact = arguments["fact"]
                        text = await self._answer_after_save(response.id, item.call_id)
                        return BrainReply(text=text, memory=fact)
                    return BrainReply(command=tool_to_command(item.name, arguments))
                except (ValueError, KeyError):
                    # Luna invented a tool or forgot an argument.
                    return BrainReply(text="Sorry, I couldn't do that.")

        # Responses API returns text through output_text.
        return BrainReply(
            text=plain_punctuation(response.output_text) or "I don't have an answer for that.",
        )

    async def say(self, message: str, instructions: str) -> str | None:
        # No tools: a line about what was done can't start anything new.
        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=[{"role": "user", "content": message}],
            )
        except OpenAIError:
            return None
        return plain_punctuation(response.output_text) or None

    async def _answer_after_save(self, response_id: str, call_id: str) -> str | None:
        # The model stops at a tool call; tell it the fact is kept so it
        # goes on to answer the owner's message in its own words.
        try:
            followup = await self._client.responses.create(
                model=self._model,
                previous_response_id=response_id,
                input=[
                    {"type": "function_call_output", "call_id": call_id, "output": "Saved."},
                ],
                tools=TOOLS,
                tool_choice="none",
            )
        except OpenAIError:
            return None
        return plain_punctuation(followup.output_text) or None
