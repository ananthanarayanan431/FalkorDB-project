from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(tags=["reset"])


@router.post("/reset")
async def post_reset(services: ServicesDep) -> ApiResponse[None]:
    await services.graph.reset()
    await services.interview_store.clear()
    await services.plans.clear()
    return ok(None, "Graph, interviews and handover plans reset")
