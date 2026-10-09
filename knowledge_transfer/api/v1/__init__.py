"""Version 1 of the HTTP API, mounted at /api/v1."""
from fastapi import APIRouter

from knowledge_transfer.api.responses import ERROR_RESPONSES
from knowledge_transfer.api.v1.routes import (
    analysis,
    handover,
    health,
    ingest,
    interviews,
    people,
    reset,
)

router = APIRouter(prefix="/api/v1", responses=ERROR_RESPONSES)
for module in (health, ingest, people, analysis, interviews, handover, reset):
    router.include_router(module.router)

__all__ = ["router"]
