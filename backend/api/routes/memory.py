from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.admin_deps import require_admin_token
from backend.config.memory_database import get_memory_session
from backend.repositories.cerebro_memory_repository import CerebroMemoryRepository
from backend.schemas.cerebro_memory import MemoryResponse, MemoryUpsertRequest, StandardMemorySchema
from backend.services.cerebro_memory_service import CerebroMemoryService

router = APIRouter(tags=["memory"])


def _service(session: Session) -> CerebroMemoryService:
    repository = CerebroMemoryRepository(session)
    return CerebroMemoryService(repository)


@router.get(
    "/api/v1/memory/{project_tag}",
    response_model=MemoryResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_memory(
    project_tag: str,
    session: Session = Depends(get_memory_session),
) -> MemoryResponse:
    service = _service(session)
    memory, source_used = service.get_memory(project_tag)
    return MemoryResponse(
        project_tag=project_tag,
        source_used=source_used,
        memory=StandardMemorySchema.model_validate(memory),
        updated_at=datetime.now(UTC),
    )


@router.post(
    "/api/v1/memory",
    response_model=MemoryResponse,
    dependencies=[Depends(require_admin_token)],
)
def upsert_memory(
    payload: MemoryUpsertRequest,
    session: Session = Depends(get_memory_session),
) -> MemoryResponse:
    service = _service(session)
    memory, source_used = service.store_memory(payload.project_tag, payload.memory.model_dump())
    return MemoryResponse(
        project_tag=payload.project_tag,
        source_used=source_used,
        memory=StandardMemorySchema.model_validate(memory),
        updated_at=datetime.now(UTC),
    )

