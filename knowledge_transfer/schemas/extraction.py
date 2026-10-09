"""Mode B and interview output: what the LLM extracts from free text."""
from typing import Literal

from pydantic import BaseModel, Field

from knowledge_transfer.schemas.sources import Kind


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
