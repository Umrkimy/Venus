from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import require_owner
from features.projects.dependencies import get_project_repository
from features.projects.models.project import Project
from features.projects.repository import ProjectRepository
from features.projects.schemas import ProjectRequest


router = APIRouter(prefix="/projects", dependencies=[Depends(require_owner)])


def project_json(project: Project) -> dict:
    return {
        "id": str(project.id),
        "name": project.name,
        "updated_at": project.updated_at.isoformat(),
    }


def project_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found",
    )


@router.get("")
def list_projects(
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    return [project_json(project) for project in projects.list_all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectRequest,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    return project_json(projects.create(request.name))


@router.patch("/{project_id}")
def rename_project(
    project_id: UUID,
    request: ProjectRequest,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    project = projects.rename(project_id, request.name)
    if project is None:
        raise project_not_found()
    return project_json(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    if not projects.delete(project_id):
        raise project_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
