from openai import AsyncOpenAI, OpenAIError

SYSTEM_PROMPT = "You are Venus, a helpful sexy assistant. Answer briefly and clearly."


class OpenAIProvider:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def reply(self, message: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
            )
        except OpenAIError:
            # No internet, wrong key, no credit: answer instead of a 500.
            return "Sorry, I couldn't process your request right now."
        # content is None when the model answers without text.
        return response.choices[0].message.content or "I don't have an answer for that."
