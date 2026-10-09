"""Postgres-backed stores used by the services. Each method runs in its own transaction."""
import uuid
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from knowledge_transfer.db.models import HandoverPlan, Interview, InterviewTurn
from knowledge_transfer.schemas.interview import Session as InterviewSession


class SqlInterviewStore:
    """Implements services.interview.InterviewStore."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def create(self, s: InterviewSession) -> None:
        async with self.sessions.begin() as db:
            db.add(Interview(id=s.id, leaver=s.leaver, status=s.status, turns=s.turns,
                             version=s.version, state=s.to_state()))

    async def get(self, id: str) -> InterviewSession | None:
        async with self.sessions() as db:
            row = await db.get(Interview, id)
            return InterviewSession.from_state(row.id, row.state, row.version) if row else None

    async def save(self, s: InterviewSession, turn: dict[str, Any] | None = None) -> bool:
        """Compare-and-set on version, recording the turn in the same transaction.
        False when another writer saved first; nothing is written then."""
        async with self.sessions.begin() as db:
            result = await db.execute(
                update(Interview)
                .where(Interview.id == s.id, Interview.version == s.version)
                .values(state=s.to_state(), version=s.version + 1, turns=s.turns, status=s.status)
            )
            if result.rowcount != 1:
                return False
            if turn:
                db.add(InterviewTurn(interview_id=s.id, seq=s.version + 1, **turn))
        return True

    async def transcript(self, id: str) -> list[dict[str, Any]]:
        async with self.sessions() as db:
            rows = await db.scalars(
                select(InterviewTurn).where(InterviewTurn.interview_id == id).order_by(InterviewTurn.seq)
            )
            return [
                {"seq": t.seq, "action": t.action, "item_id": t.item_id, "question": t.question,
                 "answer": t.answer, "answer_type": t.answer_type, "is_follow_up": t.is_follow_up,
                 "new_items": t.new_items, "created_at": t.created_at}
                for t in rows
            ]

    async def clear(self) -> None:
        async with self.sessions.begin() as db:
            await db.execute(delete(InterviewTurn))
            await db.execute(delete(Interview))


class SqlHandoverPlanStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def save(self, plan: dict[str, Any]) -> dict[str, Any]:
        row = HandoverPlan(
            leaver=plan["leaver"], receiver=plan["receiver"]["id"], strategy=plan["strategy"],
            summary=plan["summary"], step_count=len(plan["steps"]), plan=plan,
        )
        async with self.sessions.begin() as db:
            db.add(row)
            await db.flush()
            await db.refresh(row)  # load server-side created_at
            return self._full(row)

    async def get(self, id: uuid.UUID) -> dict[str, Any] | None:
        async with self.sessions() as db:
            row = await db.get(HandoverPlan, id)
            return self._full(row) if row else None

    async def list(self, leaver: str | None = None, receiver: str | None = None,
                   limit: int = 50) -> list[dict[str, Any]]:
        query = select(HandoverPlan).order_by(HandoverPlan.created_at.desc(), HandoverPlan.id).limit(limit)
        if leaver:
            query = query.where(HandoverPlan.leaver == leaver)
        if receiver:
            query = query.where(HandoverPlan.receiver == receiver)
        async with self.sessions() as db:
            return [self._summary(r) for r in await db.scalars(query)]

    async def clear(self) -> None:
        async with self.sessions.begin() as db:
            await db.execute(delete(HandoverPlan))

    @staticmethod
    def _summary(r: HandoverPlan) -> dict[str, Any]:
        return {"id": r.id, "leaver": r.leaver, "receiver": r.receiver, "strategy": r.strategy,
                "summary": r.summary, "step_count": r.step_count, "created_at": r.created_at}

    @classmethod
    def _full(cls, r: HandoverPlan) -> dict[str, Any]:
        return cls._summary(r) | {"plan": r.plan}
