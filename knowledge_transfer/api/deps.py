"""Shared services and FastAPI dependencies."""
from typing import Annotated

from fastapi import Depends, Request

from knowledge_transfer.api.errors import BadRequestError, NotFoundError
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.interview import InterviewService


class Services:
    def __init__(self, graph: KnowledgeGraph, assistant: Assistant):
        self.graph = graph
        self.assistant = assistant
        self.interviews = InterviewService(graph, assistant)


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


def resolve_leaver(services: Services, leaver: str | None) -> str:
    """The given leaver, or the person marked status=leaving."""
    found = leaver or services.graph.leaving_person()
    if not found:
        raise BadRequestError("No leaver given and none marked status=leaving; ingest sources first")
    return found


def require_person(services: Services, person: str) -> None:
    if services.graph.person(person) is None:
        raise NotFoundError(f"Unknown person {person!r}")
