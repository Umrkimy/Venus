from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.usage.models.llm_usage import LlmUsage
from features.usage.prices import cost


class UsageLog(Protocol):
    """Where the AI calls note what they used (UsageRepository, or a fake in tests)."""

    def record(self, kind: str, model: str, usage) -> None: ...


@dataclass
class UsageTotal:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    # Models used in this time with no price in prices.py, so cost_usd
    # leaves them out.
    unpriced_models: list[str] = field(default_factory=list)


class UsageRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def record(self, kind: str, model: str, usage) -> None:
        """Save what one call used, read from the SDK's usage object.

        Chat replies name cached tokens in input_tokens_details; a
        transcription's usage has no such part. None (no usage sent) is skipped.
        """
        if usage is None or getattr(usage, "input_tokens", None) is None:
            return
        details = getattr(usage, "input_tokens_details", None)
        with Session(self.engine) as session:
            session.add(LlmUsage(
                id=uuid4(),
                created_at=datetime.now(timezone.utc),
                kind=kind,
                model=model,
                input_tokens=usage.input_tokens,
                cached_tokens=getattr(details, "cached_tokens", 0) or 0,
                output_tokens=usage.output_tokens,
            ))
            session.commit()

    def total_since(self, since: datetime | None) -> UsageTotal:
        """Tokens and dollars from `since` (None = all time) until now."""
        with Session(self.engine) as session:
            query = select(
                LlmUsage.model,
                func.sum(LlmUsage.input_tokens),
                func.sum(LlmUsage.cached_tokens),
                func.sum(LlmUsage.output_tokens),
            ).group_by(LlmUsage.model).order_by(LlmUsage.model)
            if since is not None:
                query = query.where(LlmUsage.created_at >= since)
            rows = session.execute(query).all()

        total = UsageTotal()
        for model, input_tokens, cached_tokens, output_tokens in rows:
            total.input_tokens += input_tokens
            total.cached_tokens += cached_tokens
            total.output_tokens += output_tokens
            dollars = cost(model, input_tokens, cached_tokens, output_tokens)
            if dollars is None:
                total.unpriced_models.append(model)
            else:
                total.cost_usd += dollars
        return total
