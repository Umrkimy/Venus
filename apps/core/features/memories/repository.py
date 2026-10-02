from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.memories.models.memory import Memory


class MemoryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_all(self) -> list[Memory]:
        return self.newest(None)

    def newest(self, limit: int | None = 50) -> list[Memory]:
        with Session(self.engine) as session:
            query = select(Memory).order_by(Memory.created_at.desc())
            if limit is not None:
                query = query.limit(limit)
            return list(session.scalars(query).all())

    def get(self, memory_id: UUID) -> Memory | None:
        with Session(self.engine) as session:
            return session.get(Memory, memory_id)

    def create(self, text: str) -> Memory:
        text = text.strip()
        with Session(self.engine, expire_on_commit=False) as session:
            # Luna may try to save the same fact twice; keep the first one.
            existing = session.scalars(
                select(Memory).where(func.lower(Memory.text) == text.lower())
            ).first()
            if existing is not None:
                return existing
            memory = Memory(id=uuid4(), text=text, created_at=datetime.now(timezone.utc))
            session.add(memory)
            session.commit()
        return memory

    def update(self, memory_id: UUID, text: str) -> Memory | None:
        with Session(self.engine, expire_on_commit=False) as session:
            memory = session.get(Memory, memory_id)
            if memory is None:
                return None
            memory.text = text.strip()
            session.commit()
        return memory

    def delete(self, memory_id: UUID) -> bool:
        with Session(self.engine) as session:
            memory = session.get(Memory, memory_id)
            if memory is None:
                return False
            session.delete(memory)
            session.commit()
        return True
