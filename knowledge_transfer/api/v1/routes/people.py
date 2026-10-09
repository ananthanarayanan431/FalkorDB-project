from fastapi import APIRouter, status

from knowledge_transfer.api.deps import ServicesDep, require_person
from knowledge_transfer.api.errors import NotFoundError
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.models import KnowsIn, PersonIn

router = APIRouter(prefix="/people", tags=["people"])


@router.post("", status_code=status.HTTP_201_CREATED)
def post_person(person: PersonIn, services: ServicesDep) -> ApiResponse[PersonIn]:
    services.graph.upsert_person(person.id, person.name, person.role, person.seniority, person.status)
    return ok(person, "Person saved")


@router.put("/{person}/knows")
def put_knows(person: str, knows: list[KnowsIn], services: ServicesDep) -> ApiResponse[dict]:
    require_person(services, person)
    # Validate every item before writing so a bad entry leaves nothing half-applied.
    if missing := [k.item for k in knows if services.graph.item(k.item) is None]:
        raise NotFoundError(f"Unknown item {missing[0]!r}", {"missing_items": missing})
    for k in knows:
        services.graph.set_knows(person, k.item, k.level)
    return ok({"updated": len(knows)}, "Knowledge levels updated")
