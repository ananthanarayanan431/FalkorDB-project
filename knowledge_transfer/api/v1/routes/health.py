from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health(services: ServicesDep) -> ApiResponse[dict]:
    return ok({"status": "ok", "llm": services.assistant.has_llm}, "Service is healthy")
