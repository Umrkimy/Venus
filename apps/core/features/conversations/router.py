from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import require_owner
from features.conversations.dependencies import get_conversation_repository
from features.conversations.repository import ConversationRepository
from features.conversations.schemas import ConversationUpdate


router = APIRouter(prefix="/conversations")


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
):
    if not conversations.set_archived(conversation_id, request.archived):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return {"id": str(conversation_id), "archived": request.archived}


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
