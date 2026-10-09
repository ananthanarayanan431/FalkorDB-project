"""Version 1 of the HTTP API, mounted at /api/v1."""
from fastapi import APIRouter

from knowledge_transfer.api.responses import ERROR_RESPONSES
from knowledge_transfer.api.v1.routes import admin, analysis, handover, health, ingest, interviews, people

router = APIRouter(prefix="/api/v1", responses=ERROR_RESPONSES)
for module in (health, ingest, people, analysis, interviews, handover, admin):
    router.include_router(module.router)

__all__ = ["router"]
