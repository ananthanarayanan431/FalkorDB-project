"""Request bodies specific to the HTTP API. Domain models live in `knowledge_transfer.schemas`."""
from pydantic import BaseModel, Field


class BrainDumpIn(BaseModel):
    person: str = Field(min_length=1)
    text: str = Field(min_length=1)


class StartInterviewIn(BaseModel):
    leaver: str | None = None


class HandoverPlanIn(BaseModel):
    receiver: str = Field(min_length=1)
    leaver: str | None = None


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1)
