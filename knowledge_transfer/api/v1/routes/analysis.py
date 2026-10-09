from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep, resolve_leaver
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.services import gaps

router = APIRouter(tags=["analysis"])


@router.get("/gaps")
async def get_gaps(services: ServicesDep, leaver: str | None = None,
                   only_open: bool = True) -> ApiResponse[list[dict]]:
    who = await resolve_leaver(services, leaver)
    found = await gaps.open_gaps(services.graph, who) if only_open else await gaps.analyse(services.graph, who)
    return ok([g.to_dict() for g in found], f"{len(found)} gap(s) found for {who!r}")


@router.get("/coverage")
async def get_coverage(services: ServicesDep, leaver: str | None = None) -> ApiResponse[dict]:
    who = await resolve_leaver(services, leaver)
    return ok(await gaps.coverage(services.graph, who), "Coverage computed")


@router.get("/graph")
async def get_graph(services: ServicesDep) -> ApiResponse[dict]:
    return ok(await services.graph.export(), "Graph exported")
