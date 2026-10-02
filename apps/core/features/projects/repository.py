from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.conversations.models.conversation import Conversation, Message
from features.projects.models.project import Project


class ProjectRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, name: str) -> Project:
        now = datetime.now(timezone.utc)
        project = Project(id=uuid4(), name=name.strip(), created_at=now, updated_at=now)
        # Keep the values readable after commit; the route returns them.
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(project)
            session.commit()
        return project

    def list_all(self, archived: bool = False) -> list[Project]:
        if archived:
            which = Project.archived_at.is_not(None)
        else:
            which = Project.archived_at.is_(None)
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(Project).where(which).order_by(Project.updated_at.desc())
                ).all()
            )

    def chat_counts(self) -> dict[UUID, int]:
        # One query for every project; archived chats count too.
        with Session(self.engine) as session:
            rows = session.execute(
                select(Conversation.project_id, func.count())
                .where(Conversation.project_id.is_not(None))
                .group_by(Conversation.project_id)
            ).all()
        return {project_id: count for project_id, count in rows}

    def get(self, project_id: UUID) -> Project | None:
        with Session(self.engine) as session:
            return session.get(Project, project_id)

    def exists(self, project_id: UUID) -> bool:
        return self.get(project_id) is not None

    def rename(self, project_id: UUID, name: str) -> Project | None:
        with Session(self.engine, expire_on_commit=False) as session:
            project = session.get(Project, project_id)
            if project is None:
                return None
            project.name = name.strip()
            project.updated_at = datetime.now(timezone.utc)
            session.commit()
        return project

    def set_archived(self, project_id: UUID, archived: bool) -> Project | None:
        with Session(self.engine, expire_on_commit=False) as session:
            project = session.get(Project, project_id)
            if project is None:
                return None
            project.archived_at = datetime.now(timezone.utc) if archived else None
            session.commit()
        return project

    def delete(self, project_id: UUID) -> bool:
        with Session(self.engine) as session:
            project = session.get(Project, project_id)
            if project is None:
                return False
            # Messages, then chats, then the project, all in one commit,
            # so nothing is left pointing at something that is gone.
            chats = select(Conversation.id).where(Conversation.project_id == project_id)
            session.execute(delete(Message).where(Message.conversation_id.in_(chats)))
            session.execute(
                delete(Conversation).where(Conversation.project_id == project_id)
            )
            session.delete(project)
            session.commit()
        return True
