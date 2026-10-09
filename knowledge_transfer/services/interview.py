"""Graph-driven exit interview.

Each turn: pick the highest-risk open gap (or a queued follow-up), write a
question from the item's graph context, store the answer linked to the item it
explains, and add anything new the answer mentions as items. New items have no
documentation, so they surface as fresh gaps and drive later questions.

Sessions live in an `InterviewStore` (Postgres in production, see
knowledge_transfer.db), so they survive restarts and are shared between workers.
Saves are compare-and-set on a version number, and each answer or skip is
recorded as a transcript turn in the same save.
"""
import uuid
from typing import Any, Protocol

from knowledge_transfer.core.errors import InvalidState, NotFound
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.schemas.interview import Question, Session
from knowledge_transfer.services.assistant import Assistant
from knowledge_transfer.services.gaps import open_gaps
from knowledge_transfer.services.ingest import apply_extraction

__all__ = ["InterviewService", "InterviewStore", "Question", "Session"]


class InterviewStore(Protocol):
    async def create(self, session: Session) -> None: ...
    async def get(self, id: str) -> Session | None: ...
    async def save(self, session: Session, turn: dict[str, Any] | None = None) -> bool:
        """Compare-and-set on session.version; False when another writer saved first."""
        ...
    async def transcript(self, id: str) -> list[dict[str, Any]]: ...


class InterviewService:
    def __init__(self, graph: KnowledgeGraph, assistant: Assistant, store: InterviewStore):
        self.graph = graph
        self.assistant = assistant
        self.store = store

    async def start(self, leaver: str) -> tuple[Session, Question | None]:
        if await self.graph.person(leaver) is None:
            raise NotFound(f"Unknown person {leaver!r}")
        session = Session(uuid.uuid4().hex[:12], leaver)
        q = await self._advance(session)
        await self.store.create(session)
        return session, q

    async def get(self, session_id: str) -> Session:
        if (session := await self.store.get(session_id)) is None:
            raise NotFound(f"Unknown interview {session_id!r}")
        return session

    async def transcript(self, session_id: str) -> list[dict[str, Any]]:
        await self.get(session_id)
        return await self.store.transcript(session_id)

    async def _save(self, session: Session, turn: dict[str, Any] | None = None) -> None:
        if not await self.store.save(session, turn):
            raise InvalidState("Interview was updated by another request; fetch it and retry")
        session.version += 1

    async def answer(self, session_id: str, text: str, *, source: str = "interview",
                     interrupted: bool = False) -> dict:
        """`source` records how the answer arrived ("interview-voice" for spoken ones);
        `interrupted` marks an answer given before the question was fully read out."""
        session = await self.get(session_id)
        q = session.current
        if q is None:
            raise InvalidState("This interview has no open question")
        analysis = await self.assistant.analyse_answer(q.item_name, q.text, text)
        await self.graph.add_answer(q.item_id, session.leaver, q.text, text, analysis.answer_type,
                                    source=source, interrupted=interrupted)
        new_items = await apply_extraction(
            self.graph, session.leaver, analysis, "interview", ref=session.id
        )
        # Follow-ups are asked about the item the answer was about.
        if analysis.follow_up:
            session.follow_ups.append(
                Question(q.item_id, q.item_name, analysis.follow_up, ["follow-up to previous answer"], q.risk, True)
            )
        session.turns += 1
        next_question = await self._advance_dict(session)
        await self._save(session, {
            "action": "answer", "item_id": q.item_id, "question": q.text, "answer": text,
            "answer_type": analysis.answer_type, "is_follow_up": q.is_follow_up, "new_items": new_items,
        })
        return {
            "stored_for": q.item_id,
            "answer_type": analysis.answer_type,
            "new_items": new_items,
            "next_question": next_question,
        }

    async def amend(self, session_id: str, item_id: str, question: str, text: str, *,
                    source: str = "interview") -> dict:
        """Add to an answer that was already saved (the speaker kept talking while it was
        being processed). Stored against the same item; the interview does not advance."""
        session = await self.get(session_id)
        item = await self.graph.item(item_id)
        name = item["name"] if item else item_id
        analysis = await self.assistant.analyse_answer(name, question, text)
        await self.graph.add_answer(item_id, session.leaver, question, text, analysis.answer_type,
                                    source=source)
        new_items = await apply_extraction(
            self.graph, session.leaver, analysis, "interview", ref=session.id
        )
        await self._save(session, {
            "action": "amend", "item_id": item_id, "question": question, "answer": text,
            "answer_type": analysis.answer_type, "is_follow_up": False, "new_items": new_items,
        })
        return {"stored_for": item_id, "answer_type": analysis.answer_type, "new_items": new_items}

    async def skip(self, session_id: str) -> dict:
        session = await self.get(session_id)
        turn = None
        if (q := session.current) is not None:
            session.skipped.add(q.item_id)
            turn = {"action": "skip", "item_id": q.item_id, "question": q.text,
                    "is_follow_up": q.is_follow_up}
        next_question = await self._advance_dict(session)
        await self._save(session, turn)
        return {"next_question": next_question}

    async def _advance_dict(self, session):
        q = await self._advance(session)
        return q.to_dict() if q else None

    async def _advance(self, session: Session) -> Question | None:
        if session.follow_ups:
            session.current = session.follow_ups.pop(0)
            return session.current
        for gap in await open_gaps(self.graph, session.leaver):
            if gap.item_id in session.skipped:
                continue
            text = await self.assistant.write_question(gap, await self.graph.related(gap.item_id))
            session.current = Question(gap.item_id, gap.name, text, gap.reasons, gap.risk)
            return session.current
        session.current = None
        return None
