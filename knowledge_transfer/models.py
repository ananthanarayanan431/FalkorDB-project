"""Pydantic models shared by ingest, the services and the API."""
import re
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["system", "decision", "topic"]
Seniority = Literal["junior", "mid", "senior"]
Touch = Literal["OWNS", "WORKED_ON", "AUTHORED"]
SourceType = Literal["ticket", "doc", "code", "interview", "braindump"]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---- mode A: structured company sources ---------------------------------

class PersonIn(BaseModel):
    id: str
    name: str
    role: str = ""
    seniority: Seniority = "mid"
    status: Literal["active", "leaving"] = "active"


class ItemIn(BaseModel):
    id: str
    name: str
    kind: Kind = "topic"
    description: str = ""


class DocumentIn(BaseModel):
    id: str
    title: str
    covers: list[str] = Field(default_factory=list, description="item ids this document documents")


class ContributionIn(BaseModel):
    person: str
    item: str
    rel: Touch = "WORKED_ON"
    source: SourceType = "ticket"
    ref: str = ""


class LinkIn(BaseModel):
    src: str
    rel: Literal["DEPENDS_ON", "PREREQUISITE_OF"]
    dst: str


class KnowsIn(BaseModel):
    person: str
    item: str
    level: int = Field(2, ge=1, le=3, description="1 aware, 2 working, 3 expert")


class SourceBundle(BaseModel):
    people: list[PersonIn] = Field(default_factory=list)
    items: list[ItemIn] = Field(default_factory=list)
    documents: list[DocumentIn] = Field(default_factory=list)
    contributions: list[ContributionIn] = Field(default_factory=list)
    links: list[LinkIn] = Field(default_factory=list)
    knows: list[KnowsIn] = Field(default_factory=list)


# ---- mode B / interview: what the LLM extracts from free text ------------

class ExtractedItem(BaseModel):
    name: str
    kind: Kind = "topic"
    description: str = ""
    owned: bool = False
    depends_on: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(
        default_factory=list, description="things to understand before this one"
    )


class Extraction(BaseModel):
    items: list[ExtractedItem] = Field(default_factory=list)


class AnswerAnalysis(Extraction):
    answer_type: Literal["rationale", "trap", "procedure", "contact", "other"] = "other"
    follow_up: str | None = Field(
        None, description="one follow-up question if the answer is vague or opens a new gap"
    )
