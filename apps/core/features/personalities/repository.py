from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.personalities.models.personality import Personality


class PersonalityRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_all(self) -> list[Personality]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(Personality).order_by(Personality.created_at)
                ).all()
            )

    def get(self, personality_id: UUID) -> Personality | None:
        with Session(self.engine) as session:
            return session.get(Personality, personality_id)

    def active(self) -> Personality | None:
        with Session(self.engine) as session:
            return session.scalars(
                select(Personality).where(Personality.active.is_(True))
            ).first()

    def create(self, name: str, text: str) -> Personality:
        now = datetime.now(timezone.utc)
        # New ones start switched off; the owner activates one on purpose.
        personality = Personality(
            id=uuid4(),
            name=name.strip(),
            text=text.strip(),
            active=False,
            created_at=now,
            updated_at=now,
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(personality)
            session.commit()
        return personality

    def update(
        self,
        personality_id: UUID,
        name: str | None,
        text: str | None,
    ) -> Personality | None:
        with Session(self.engine, expire_on_commit=False) as session:
            personality = session.get(Personality, personality_id)
            if personality is None:
                return None
            if name is not None:
                personality.name = name.strip()
            if text is not None:
                personality.text = text.strip()
            personality.updated_at = datetime.now(timezone.utc)
            session.commit()
        return personality

    def activate(self, personality_id: UUID) -> None:
        # One commit switches the old one off and the new one on,
        # so there is never a moment with two (or zero) active.
        with Session(self.engine) as session:
            for personality in session.scalars(select(Personality)):
                personality.active = personality.id == personality_id
            session.commit()

    def delete(self, personality_id: UUID) -> bool:
        with Session(self.engine) as session:
            personality = session.get(Personality, personality_id)
            if personality is None:
                return False
            session.delete(personality)
            session.commit()
        return True
