from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.conversations.models.conversation import Conversation
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

    def list_all(self) -> list[Project]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(Project).order_by(Project.updated_at.desc())
                ).all()
            )

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

    def delete(self, project_id: UUID) -> bool:
        with Session(self.engine) as session:
            project = session.get(Project, project_id)
            if project is None:
                return False
            # Its chats stay; they just leave the project, in the same commit.
            session.execute(
                update(Conversation)
                .where(Conversation.project_id == project_id)
                .values(project_id=None)
            )
            session.delete(project)
            session.commit()
        return True
