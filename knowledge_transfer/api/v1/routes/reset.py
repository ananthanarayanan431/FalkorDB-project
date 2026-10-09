from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.core.config import get_settings
from knowledge_transfer.core.errors import NotFound

router = APIRouter(tags=["reset"])


@router.post("/reset")
async def post_reset(services: ServicesDep) -> ApiResponse[None]:
    if not get_settings().enable_reset:
        raise NotFound("Reset is disabled; set ENABLE_RESET=true to enable it")
    await services.graph.reset()
    await services.interview_store.clear()
    await services.plans.clear()
    return ok(None, "Graph, interviews and handover plans reset")
