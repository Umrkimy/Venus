from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import require_owner
from features.conversations.dependencies import get_conversation_repository
from features.conversations.repository import ConversationRepository
from features.conversations.schemas import ConversationUpdate
from features.projects.dependencies import get_project_repository
from features.projects.repository import ProjectRepository
from features.projects.router import require_open_project


router = APIRouter(prefix="/conversations")


def project_id_json(project_id: UUID | None) -> str | None:
    return None if project_id is None else str(project_id)


@router.get("", dependencies=[Depends(require_owner)])
def list_conversations(
    conversations: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
    archived: bool = False,
):
    return [
        {
            "id": str(conversation.id),
            "title": conversation.title,
            "updated_at": conversation.updated_at.isoformat(),
            "project_id": project_id_json(conversation.project_id),
        }
        for conversation in conversations.list_all(archived)
    ]


@router.get("/{conversation_id}", dependencies=[Depends(require_owner)])
def get_conversation(
    conversation_id: UUID,
    conversations: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
):
    conversation = conversations.get(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in conversations.messages(conversation_id)
        ],
    }


@router.patch("/{conversation_id}", dependencies=[Depends(require_owner)])
def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdate,
    conversations: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
):
    if conversations.get(conversation_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    # model_fields_set holds only the fields the request sent, so
    # {"archived": true} leaves the project alone and {"project_id": null} clears it.
    move = "project_id" in request.model_fields_set
    if move and request.project_id is not None:
        require_open_project(projects, request.project_id)
    if request.archived is not None:
        conversations.set_archived(conversation_id, request.archived)
    if move:
        conversations.set_project(conversation_id, request.project_id)
    conversation = conversations.get(conversation_id)
    return {
        "id": str(conversation_id),
        "archived": conversation.archived_at is not None,
        "project_id": project_id_json(conversation.project_id),
    }


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_owner)],
)
def delete_conversation(
    conversation_id: UUID,
    conversations: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
):
    if not conversations.delete(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
