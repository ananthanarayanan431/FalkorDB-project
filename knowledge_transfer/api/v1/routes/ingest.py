from fastapi import APIRouter, status

from knowledge_transfer.api.deps import ServicesDep, require_person
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.api.schemas import BrainDumpIn
from knowledge_transfer.schemas import SourceBundle
from knowledge_transfer.seed.northwind import BUNDLE
from knowledge_transfer.services.ingest import ingest_braindump, ingest_sources

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/sources", status_code=status.HTTP_201_CREATED)
async def post_sources(bundle: SourceBundle, services: ServicesDep) -> ApiResponse[dict]:
    return ok(await ingest_sources(services.graph, bundle), "Sources ingested")


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def post_seed(services: ServicesDep) -> ApiResponse[dict]:
    return ok(await ingest_sources(services.graph, BUNDLE), "Seed data ingested")


@router.post("/braindump", status_code=status.HTTP_201_CREATED)
async def post_braindump(body: BrainDumpIn, services: ServicesDep) -> ApiResponse[dict]:
    await require_person(services, body.person)
    result = await ingest_braindump(services.graph, services.assistant, body.person, body.text)
    return ok(result, "Brain dump ingested")
