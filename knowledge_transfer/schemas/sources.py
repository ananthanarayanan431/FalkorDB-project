"""Mode A input: structured company sources (people, items, docs, contributions).

Every string and list has an upper bound, so one request cannot store unbounded text or
make the server walk an enormous bundle. The body size limit in the API middleware is the
outer guard; these bounds give clear, per-field validation errors.
"""
import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Kind = Literal["system", "decision", "topic"]
Seniority = Literal["junior", "mid", "senior"]
Touch = Literal["OWNS", "WORKED_ON", "AUTHORED"]
SourceType = Literal["ticket", "doc", "code", "interview", "braindump"]

MAX_ID = 200
MAX_NAME = 300
MAX_DESCRIPTION = 5_000
MAX_LIST = 10_000

Id = Annotated[str, Field(min_length=1, max_length=MAX_ID)]
Name = Annotated[str, Field(min_length=1, max_length=MAX_NAME)]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class PersonIn(BaseModel):
    id: Id
    name: Name
    role: str = Field("", max_length=MAX_NAME)
    seniority: Seniority = "mid"
    status: Literal["active", "leaving"] = "active"


class ItemIn(BaseModel):
    id: Id
    name: Name
    kind: Kind = "topic"
    description: str = Field("", max_length=MAX_DESCRIPTION)


class DocumentIn(BaseModel):
    id: Id
    title: Name
    covers: list[Id] = Field(default_factory=list, max_length=MAX_LIST,
                             description="item ids this document documents")


class ContributionIn(BaseModel):
    person: Id
    item: Id
    rel: Touch = "WORKED_ON"
    source: SourceType = "ticket"
    ref: str = Field("", max_length=MAX_NAME)


class LinkIn(BaseModel):
    src: Id
    rel: Literal["DEPENDS_ON", "PREREQUISITE_OF"]
    dst: Id


class KnowsLevelIn(BaseModel):
    item: Id
    level: int = Field(2, ge=1, le=3, description="1 aware, 2 working, 3 expert")


class KnowsIn(KnowsLevelIn):
    person: Id


class SourceBundle(BaseModel):
    people: list[PersonIn] = Field(default_factory=list, max_length=MAX_LIST)
    items: list[ItemIn] = Field(default_factory=list, max_length=MAX_LIST)
    documents: list[DocumentIn] = Field(default_factory=list, max_length=MAX_LIST)
    contributions: list[ContributionIn] = Field(default_factory=list, max_length=MAX_LIST)
    links: list[LinkIn] = Field(default_factory=list, max_length=MAX_LIST)
    knows: list[KnowsIn] = Field(default_factory=list, max_length=MAX_LIST)
