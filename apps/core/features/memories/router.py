from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import require_owner
from features.memories.dependencies import get_memory_repository
from features.memories.models.memory import Memory
from features.memories.repository import MemoryRepository
from features.memories.schemas import MemoryRequest


router = APIRouter(prefix="/memories", dependencies=[Depends(require_owner)])


def memory_json(memory: Memory) -> dict:
    return {
        "id": str(memory.id),
        "text": memory.text,
        "created_at": memory.created_at.isoformat(),
    }


def memory_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Memory not found",
    )


@router.get("")
def list_memories(
    memories: Annotated[MemoryRepository, Depends(get_memory_repository)],
):
    return [memory_json(memory) for memory in memories.list_all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_memory(
    request: MemoryRequest,
    memories: Annotated[MemoryRepository, Depends(get_memory_repository)],
):
    return memory_json(memories.create(request.text))


@router.patch("/{memory_id}")
def update_memory(
    memory_id: UUID,
    request: MemoryRequest,
    memories: Annotated[MemoryRepository, Depends(get_memory_repository)],
):
    memory = memories.update(memory_id, request.text)
    if memory is None:
        raise memory_not_found()
    return memory_json(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: UUID,
    memories: Annotated[MemoryRepository, Depends(get_memory_repository)],
):
    if not memories.delete(memory_id):
        raise memory_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
