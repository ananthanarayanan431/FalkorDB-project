from fastapi import APIRouter, status

from knowledge_transfer.api.deps import ServicesDep, require_person
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.api.schemas import BrainDumpIn
from knowledge_transfer.ingest import ingest_braindump, ingest_sources
from knowledge_transfer.models import SourceBundle
from knowledge_transfer.seed.northwind import BUNDLE

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/sources", status_code=status.HTTP_201_CREATED)
def post_sources(bundle: SourceBundle, services: ServicesDep) -> ApiResponse[dict]:
    return ok(ingest_sources(services.graph, bundle), "Sources ingested")


@router.post("/seed", status_code=status.HTTP_201_CREATED)
def post_seed(services: ServicesDep) -> ApiResponse[dict]:
    return ok(ingest_sources(services.graph, BUNDLE), "Seed data ingested")


@router.post("/braindump", status_code=status.HTTP_201_CREATED)
def post_braindump(body: BrainDumpIn, services: ServicesDep) -> ApiResponse[dict]:
    require_person(services, body.person)
    result = ingest_braindump(services.graph, services.assistant, body.person, body.text)
    return ok(result, "Brain dump ingested")
