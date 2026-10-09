from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
def post_reset(services: ServicesDep) -> ApiResponse[None]:
    services.graph.reset()
    services.interviews.sessions.clear()
    return ok(None, "Graph and interview sessions reset")
