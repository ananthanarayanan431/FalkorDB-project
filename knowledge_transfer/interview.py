"""Graph-driven exit interview.

Each turn: pick the highest-risk open gap (or a queued follow-up), write a
question from the item's graph context, store the answer linked to the item it
explains, and add anything new the answer mentions as items. New items have no
documentation, so they surface as fresh gaps and drive later questions.
"""
import uuid
from dataclasses import dataclass, field

from knowledge_transfer.assistant import Assistant
from knowledge_transfer.errors import InvalidState, NotFound
from knowledge_transfer.gaps import open_gaps
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.ingest import apply_extraction


@dataclass
class Question:
    item_id: str
    item_name: str
    text: str
    reasons: list[str]
    risk: int
    is_follow_up: bool = False

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class Session:
    id: str
    leaver: str
    current: Question | None = None
    follow_ups: list[Question] = field(default_factory=list)
    skipped: set[str] = field(default_factory=set)
    turns: int = 0


class InterviewService:
    def __init__(self, graph: KnowledgeGraph, assistant: Assistant):
        self.graph = graph
        self.assistant = assistant
        self.sessions: dict[str, Session] = {}

    def start(self, leaver: str) -> tuple[Session, Question | None]:
        if self.graph.person(leaver) is None:
            raise NotFound(f"Unknown person {leaver!r}")
        session = Session(uuid.uuid4().hex[:12], leaver)
        self.sessions[session.id] = session
        return session, self._advance(session)

    def get(self, session_id: str) -> Session:
        if (session := self.sessions.get(session_id)) is None:
            raise NotFound(f"Unknown interview {session_id!r}")
        return session

    def answer(self, session_id: str, text: str) -> dict:
        session = self.get(session_id)
        q = session.current
        if q is None:
            raise InvalidState("This interview has no open question")
        analysis = self.assistant.analyse_answer(q.item_name, q.text, text)
        self.graph.add_answer(q.item_id, session.leaver, q.text, text, analysis.answer_type)
        new_items = apply_extraction(
            self.graph, session.leaver, analysis, "interview", ref=session.id
        )
        # Follow-ups are asked about the item the answer was about.
        if analysis.follow_up:
            session.follow_ups.append(
                Question(q.item_id, q.item_name, analysis.follow_up, ["follow-up to previous answer"], q.risk, True)
            )
        session.turns += 1
        return {
            "stored_for": q.item_id,
            "answer_type": analysis.answer_type,
            "new_items": new_items,
            "next_question": self._advance_dict(session),
        }

    def skip(self, session_id: str) -> dict:
        session = self.get(session_id)
        if session.current is not None:
            session.skipped.add(session.current.item_id)
        return {"next_question": self._advance_dict(session)}

    def _advance_dict(self, session):
        q = self._advance(session)
        return q.to_dict() if q else None

    def _advance(self, session: Session) -> Question | None:
        if session.follow_ups:
            session.current = session.follow_ups.pop(0)
            return session.current
        for gap in open_gaps(self.graph, session.leaver):
            if gap.item_id in session.skipped:
                continue
            text = self.assistant.write_question(gap, self.graph.related(gap.item_id))
            session.current = Question(gap.item_id, gap.name, text, gap.reasons, gap.risk)
            return session.current
        session.current = None
        return None
