"""ORM models. FalkorDB holds the knowledge graph; Postgres holds interview
sessions, their transcripts and the handover plans generated from the graph."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from knowledge_transfer.db.base import Base, JSONType, TimestampMixin


class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    leaver: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | completed
    turns: Mapped[int] = mapped_column(Integer, default=0)
    # Optimistic lock: every save must name the version it read.
    version: Mapped[int] = mapped_column(Integer, default=0)
    # Serialised interview.Session (current question, follow-up queue, skipped items).
    state: Mapped[dict[str, Any]] = mapped_column(JSONType)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    transcript: Mapped[list["InterviewTurn"]] = relationship(
        back_populates="interview", order_by="InterviewTurn.seq",
        cascade="all, delete-orphan", passive_deletes=True,
        lazy="raise",  # async: load explicitly, never implicitly
    )


class InterviewTurn(TimestampMixin, Base):
    __tablename__ = "interview_turns"
    __table_args__ = (UniqueConstraint("interview_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id: Mapped[str] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))  # answer | skip
    item_id: Mapped[str] = mapped_column(String(255))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    answer_type: Mapped[str | None] = mapped_column(String(32))
    is_follow_up: Mapped[bool] = mapped_column(default=False)
    new_items: Mapped[list[str]] = mapped_column(JSONType, default=list)

    interview: Mapped[Interview] = relationship(back_populates="transcript", lazy="raise")


class HandoverPlan(TimestampMixin, Base):
    __tablename__ = "handover_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    leaver: Mapped[str] = mapped_column(String(255), index=True)
    receiver: Mapped[str] = mapped_column(String(255), index=True)
    strategy: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    step_count: Mapped[int] = mapped_column(Integer)
    plan: Mapped[dict[str, Any]] = mapped_column(JSONType)
