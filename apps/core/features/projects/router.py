from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import require_owner
from features.projects.dependencies import get_project_repository
from features.projects.models.project import Project
from features.projects.repository import ProjectRepository
from features.projects.schemas import ProjectRequest, ProjectUpdate


router = APIRouter(prefix="/projects", dependencies=[Depends(require_owner)])


def project_json(project: Project, chat_count: int) -> dict:
    return {
        "id": str(project.id),
        "name": project.name,
        "updated_at": project.updated_at.isoformat(),
        "archived": project.archived_at is not None,
        "instructions": project.instructions,
        # Archived chats count too: deleting the project deletes them all.
        "chat_count": chat_count,
    }


def project_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found",
    )


def require_open_project(projects: ProjectRepository, project_id: UUID) -> None:
    """Chats can only go into a project that exists and isn't archived."""
    project = projects.get(project_id)
    if project is None:
        raise project_not_found()
    if project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is archived",
        )


@router.get("")
def list_projects(
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    archived: bool = False,
):
    counts = projects.chat_counts()
    return [
        project_json(project, counts.get(project.id, 0))
        for project in projects.list_all(archived)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectRequest,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    return project_json(projects.create(request.name), 0)


@router.patch("/{project_id}")
def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    if not projects.exists(project_id):
        raise project_not_found()
    if request.name is not None:
        projects.rename(project_id, request.name)
    if request.archived is not None:
        projects.set_archived(project_id, request.archived)
    if request.instructions is not None:
        projects.set_instructions(project_id, request.instructions)
    project = projects.get(project_id)
    return project_json(project, projects.chat_counts().get(project_id, 0))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    if not projects.delete(project_id):
        raise project_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
