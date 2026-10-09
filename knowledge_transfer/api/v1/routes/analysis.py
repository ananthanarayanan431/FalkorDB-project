from fastapi import APIRouter

from knowledge_transfer import gaps
from knowledge_transfer.api.deps import ServicesDep, resolve_leaver
from knowledge_transfer.api.responses import ApiResponse, ok

router = APIRouter(tags=["analysis"])


@router.get("/gaps")
def get_gaps(services: ServicesDep, leaver: str | None = None,
             only_open: bool = True) -> ApiResponse[list[dict]]:
    who = resolve_leaver(services, leaver)
    found = gaps.open_gaps(services.graph, who) if only_open else gaps.analyse(services.graph, who)
    return ok([g.to_dict() for g in found], f"{len(found)} gap(s) found for {who!r}")


@router.get("/coverage")
def get_coverage(services: ServicesDep, leaver: str | None = None) -> ApiResponse[dict]:
    who = resolve_leaver(services, leaver)
    return ok(gaps.coverage(services.graph, who), "Coverage computed")


@router.get("/graph")
def get_graph(services: ServicesDep) -> ApiResponse[dict]:
    return ok(services.graph.export(), "Graph exported")
