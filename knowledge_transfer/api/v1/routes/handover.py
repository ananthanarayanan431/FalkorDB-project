import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from knowledge_transfer import handover
from knowledge_transfer.api.deps import ServicesDep, resolve_leaver
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.api.schemas import HandoverPlanIn
from knowledge_transfer.errors import NotFound

router = APIRouter(tags=["handover"])


@router.get("/handover/{receiver}")
async def preview_handover(receiver: str, services: ServicesDep, leaver: str | None = None) -> ApiResponse[dict]:
    """Build a plan from the current graph without saving it."""
    who = await resolve_leaver(services, leaver)
    plan = await handover.build_plan(services.graph, services.assistant, who, receiver)
    return ok(plan, "Handover plan built")


@router.post("/handover-plans", status_code=status.HTTP_201_CREATED)
async def create_handover_plan(body: HandoverPlanIn, services: ServicesDep) -> ApiResponse[dict]:
    """Build a plan and store it, so the receiver keeps the version they were given."""
    who = await resolve_leaver(services, body.leaver)
    plan = await handover.build_plan(services.graph, services.assistant, who, body.receiver)
    return ok(await services.plans.save(plan), "Handover plan saved")


@router.get("/handover-plans")
async def list_handover_plans(
    services: ServicesDep,
    leaver: str | None = None,
    receiver: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ApiResponse[list[dict]]:
    plans = await services.plans.list(leaver, receiver, limit)
    return ok(plans, f"{len(plans)} handover plan(s) found")


@router.get("/handover-plans/{plan_id}")
async def get_handover_plan(plan_id: uuid.UUID, services: ServicesDep) -> ApiResponse[dict]:
    if (plan := await services.plans.get(plan_id)) is None:
        raise NotFound(f"Unknown handover plan {str(plan_id)!r}")
    return ok(plan, "Handover plan found")
