"""Shared services and FastAPI dependencies."""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from knowledge_transfer.api.errors import BadRequestError
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.db import SqlHandoverPlanStore, SqlInterviewStore
from knowledge_transfer.errors import NotFound
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.interview import InterviewService


class Services:
    """FalkorDB for the knowledge graph, Postgres (`db`) for sessions and results."""

    def __init__(self, graph: KnowledgeGraph, assistant: Assistant,
                 db: async_sessionmaker[AsyncSession]):
        self.graph = graph
        self.assistant = assistant
        self.db = db
        self.interview_store = SqlInterviewStore(db)
        self.plans = SqlHandoverPlanStore(db)
        self.interviews = InterviewService(graph, assistant, self.interview_store)


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


async def require_person(services: Services, person: str) -> None:
    if await services.graph.person(person) is None:
        raise NotFound(f"Unknown person {person!r}")


async def resolve_leaver(services: Services, leaver: str | None) -> str:
    """The given leaver (which must exist), or the person marked status=leaving."""
    if leaver:
        await require_person(services, leaver)
        return leaver
    if found := await services.graph.leaving_person():
        return found
    raise BadRequestError("No leaver given and none marked status=leaving; ingest sources first")
