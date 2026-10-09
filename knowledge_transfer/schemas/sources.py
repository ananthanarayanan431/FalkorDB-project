"""Mode A input: structured company sources (people, items, docs, contributions)."""
import re
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["system", "decision", "topic"]
Seniority = Literal["junior", "mid", "senior"]
Touch = Literal["OWNS", "WORKED_ON", "AUTHORED"]
SourceType = Literal["ticket", "doc", "code", "interview", "braindump"]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


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


class KnowsLevelIn(BaseModel):
    item: str
    level: int = Field(2, ge=1, le=3, description="1 aware, 2 working, 3 expert")


class KnowsIn(KnowsLevelIn):
    person: str


class SourceBundle(BaseModel):
    people: list[PersonIn] = Field(default_factory=list)
    items: list[ItemIn] = Field(default_factory=list)
    documents: list[DocumentIn] = Field(default_factory=list)
    contributions: list[ContributionIn] = Field(default_factory=list)
    links: list[LinkIn] = Field(default_factory=list)
    knows: list[KnowsIn] = Field(default_factory=list)
