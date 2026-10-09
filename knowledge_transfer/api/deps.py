"""Shared services and FastAPI dependencies."""
import os
import secrets
from typing import Annotated

from fastapi import Depends, Header, Request

from knowledge_transfer.api.errors import BadRequestError, ForbiddenError, UnauthorizedError
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.errors import NotFound
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


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    """Admin routes need X-Admin-Token to match KT_ADMIN_TOKEN; with no token set they are off."""
    expected = os.getenv("KT_ADMIN_TOKEN")
    if not expected:
        raise ForbiddenError("Admin endpoints are disabled; set KT_ADMIN_TOKEN to enable them")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise UnauthorizedError("Missing or invalid X-Admin-Token header")


def require_person(services: Services, person: str) -> None:
    if services.graph.person(person) is None:
        raise NotFound(f"Unknown person {person!r}")


def resolve_leaver(services: Services, leaver: str | None) -> str:
    """The given leaver (which must exist), or the person marked status=leaving."""
    if leaver:
        require_person(services, leaver)
        return leaver
    if found := services.graph.leaving_person():
        return found
    raise BadRequestError("No leaver given and none marked status=leaving; ingest sources first")
