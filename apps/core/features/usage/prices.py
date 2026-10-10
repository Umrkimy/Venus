# US dollars per 1 million tokens: (input, cached input, output).
# From OpenAI's pricing page (developers.openai.com/api/docs/pricing),
# checked 2026-10-11. Add a model here when you switch to it; without a
# price Venus still counts its tokens but can't say what they cost.
PRICES: dict[str, tuple[float, float, float]] = {
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
    "gpt-5-nano": (0.05, 0.005, 0.40),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-4o-mini": (0.15, 0.075, 0.60),
    # Audio in, text out; no cache discount.
    "gpt-4o-mini-transcribe": (1.25, 1.25, 5.00),
}


def cost(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float | None:
    """Dollars for these tokens, or None when the model has no price here."""
    price = PRICES.get(model)
    if price is None:
        return None
    input_price, cached_price, output_price = price
    # Cached tokens are part of input_tokens, billed at the cheaper rate.
    fresh_tokens = input_tokens - cached_tokens
    return (
        fresh_tokens * input_price
        + cached_tokens * cached_price
        + output_tokens * output_price
    ) / 1_000_000
