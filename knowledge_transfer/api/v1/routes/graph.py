"""The knowledge graph as stored in FalkorDB, for browsing and visualisation. Read-only."""
from typing import Annotated

from fastapi import APIRouter, Path, Query

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.core.errors import NotFound

router = APIRouter(prefix="/graph", tags=["graph"])

MAX_NODES = 5000


@router.get("")
async def get_graph(services: ServicesDep) -> ApiResponse[dict]:
    """Every node and edge with a display name only. See /graph/snapshot for all properties."""
    return ok(await services.graph.export(), "Graph exported")


@router.get("/schema")
async def get_schema(services: ServicesDep) -> ApiResponse[dict]:
    """Totals, plus how many nodes carry each label and how many edges have each type."""
    return ok(await services.graph.schema(), "Graph schema")


@router.get("/snapshot")
async def get_snapshot(
    services: ServicesDep,
    labels: Annotated[list[str] | None, Query(description="Only nodes with one of these labels")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_NODES)] = 1000,
) -> ApiResponse[dict]:
    """Nodes with all their labels and properties, and every relationship between them.
    `truncated` is true when more nodes matched than `limit`."""
    snap = await services.graph.snapshot(labels, limit)
    note = f" (first {limit} nodes)" if snap["truncated"] else ""
    return ok(snap, f"{len(snap['nodes'])} node(s) and {len(snap['edges'])} relationship(s){note}")


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(
    services: ServicesDep,
    node_id: Annotated[int, Path(ge=0, description="FalkorDB internal node id, as in /graph/snapshot")],
    limit: Annotated[int, Query(ge=1, le=MAX_NODES)] = 500,
) -> ApiResponse[dict]:
    """A node, its relationships in both directions and the nodes they connect to."""
    if (found := await services.graph.neighbors(node_id, limit)) is None:
        raise NotFound(f"Unknown node {node_id}")
    return ok(found, f"{len(found['edges'])} relationship(s)")
