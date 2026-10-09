from fastapi import APIRouter, Depends

from knowledge_transfer.api.deps import ServicesDep, require_admin
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/reset")
def post_reset(services: ServicesDep) -> ApiResponse[None]:
    services.graph.reset()  # interview sessions are graph nodes, so this clears them too
    return ok(None, "Graph and interview sessions reset")
