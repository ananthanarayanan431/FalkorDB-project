"""Request bodies specific to the HTTP API. Domain models live in `knowledge_transfer.schemas`."""
from pydantic import BaseModel, Field

from knowledge_transfer.schemas.sources import Id

# Free text goes to the language model and into the graph; keep it to what a person writes.
MAX_ANSWER_CHARS = 10_000
MAX_BRAINDUMP_CHARS = 20_000


class BrainDumpIn(BaseModel):
    person: Id
    text: str = Field(min_length=1, max_length=MAX_BRAINDUMP_CHARS)


class StartInterviewIn(BaseModel):
    leaver: Id | None = None


class HandoverPlanIn(BaseModel):
    receiver: Id
    leaver: Id | None = None


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_CHARS)
