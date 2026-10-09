from fastapi import APIRouter

from knowledge_transfer import handover
from knowledge_transfer.api.deps import ServicesDep, resolve_leaver
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(prefix="/handover", tags=["handover"])


@router.get("/{receiver}")
def get_handover(receiver: str, services: ServicesDep, leaver: str | None = None) -> ApiResponse[dict]:
    who = resolve_leaver(services, leaver)
    plan = handover.build_plan(services.graph, services.assistant, who, receiver)
    return ok(plan, "Handover plan built")
