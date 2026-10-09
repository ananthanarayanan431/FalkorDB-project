from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.errors import ServiceUnavailableError
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.db import ping

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(services: ServicesDep) -> ApiResponse[dict]:
    checks = {
        "graph": "up" if await services.graph.ping() else "down",
        "database": "up" if await ping(services.db) else "down",
    }
    if "down" in checks.values():
        raise ServiceUnavailableError("A backing store is unreachable", checks)
    return ok({"status": "ok", **checks, "llm": services.assistant.has_llm}, "Service is healthy")
