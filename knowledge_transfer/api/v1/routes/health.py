import asyncio
from collections.abc import Awaitable

from fastapi import APIRouter

from knowledge_transfer.api.deps import ServicesDep
from knowledge_transfer.api.errors import ServiceUnavailableError
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.db import ping

router = APIRouter(tags=["health"])

# A store that does not answer within this is reported down, so a hung store cannot hang
# the health check (and whatever probe calls it) with it.
PING_TIMEOUT_S = 3.0


async def _up(check: Awaitable[bool]) -> str:
    try:
        async with asyncio.timeout(PING_TIMEOUT_S):
            return "up" if await check else "down"
    except TimeoutError:
        return "down"


@router.get("/health")
async def health(services: ServicesDep) -> ApiResponse[dict]:
    graph, database = await asyncio.gather(_up(services.graph.ping()), _up(ping(services.db)))
    checks = {"graph": graph, "database": database}
    if "down" in checks.values():
        raise ServiceUnavailableError("A backing store is unreachable", checks)
    return ok({"status": "ok", **checks, "llm": services.assistant.has_llm}, "Service is healthy")
