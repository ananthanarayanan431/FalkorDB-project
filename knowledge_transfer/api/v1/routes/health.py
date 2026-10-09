from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.errors import ServiceUnavailableError
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health(services: ServicesDep) -> ApiResponse[dict]:
    if not services.graph.ping():
        raise ServiceUnavailableError("Graph database is unreachable", {"database": "down"})
    return ok({"status": "ok", "database": "up", "llm": services.assistant.has_llm}, "Service is healthy")
