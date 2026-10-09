from fakes import FakeLLM

from knowledge_transfer import gaps
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.interview import InterviewService
from knowledge_transfer.models import AnswerAnalysis, ExtractedItem


def test_first_question_targets_highest_risk_open_gap(seeded, assistant):
    svc = InterviewService(seeded, assistant)
    _, q = svc.start("ravi")
    top = gaps.open_gaps(seeded, "ravi")[0]
    assert q.item_id == top.item_id
    assert "only person" in q.text and q.reasons == top.reasons


def test_answer_is_stored_and_closes_the_gap(seeded, assistant):
    svc = InterviewService(seeded, assistant)
    session, q = svc.start("ravi")
    out = svc.answer(session.id, "Gateway rate-limit window is 30 min; 40 gives margin.")
    assert out["stored_for"] == q.item_id
    assert out["next_question"]["item_id"] != q.item_id
    assert seeded.answers_for([q.item_id])[q.item_id][0]["source"] == "interview"


def test_interview_ends_when_no_open_gaps(seeded, assistant):
    svc = InterviewService(seeded, assistant)
    session, q = svc.start("ravi")
    n = 0
    while q is not None and n < 50:
        q = svc.answer(session.id, "because") and svc.get(session.id).current
        n += 1
    assert gaps.coverage(seeded, "ravi")["percent"] == 100.0


def test_skip_does_not_repeat_the_question(seeded, assistant):
    svc = InterviewService(seeded, assistant)
    session, q = svc.start("ravi")
    nxt = svc.skip(session.id)["next_question"]
    assert nxt["item_id"] != q.item_id


def test_llm_answer_creates_new_gap_and_follow_up(seeded):
    analysis = AnswerAnalysis(
        answer_type="trap",
        items=[ExtractedItem(name="Nightly cron host", kind="system", depends_on=["Ledger sync job"])],
        follow_up="Who has access to the cron host?",
    )
    svc = InterviewService(seeded, Assistant(FakeLLM({AnswerAnalysis: analysis}, text="LLM question?")))
    session, q = svc.start("ravi")
    assert q.text == "LLM question?"
    out = svc.answer(session.id, "It also needs the cron host restarted manually.")
    assert out["new_items"] == ["nightly-cron-host"]
    assert out["answer_type"] == "trap"
    assert out["next_question"]["is_follow_up"] and out["next_question"]["item_id"] == q.item_id
    assert "nightly-cron-host" in {g.item_id for g in gaps.open_gaps(seeded, "ravi")}


def test_unknown_leaver(graph, assistant):
    import pytest
    from knowledge_transfer.errors import NotFound
    with pytest.raises(NotFound):
        InterviewService(graph, assistant).start("nobody")


def test_llm_failure_falls_back_to_templates(seeded):
    class BrokenLLM:
        def invoke(self, _msgs):
            raise ConnectionError("provider down")

        def with_structured_output(self, _schema):
            return self

    svc = InterviewService(seeded, Assistant(BrokenLLM()))
    session, q = svc.start("ravi")
    assert "only person" in q.text  # template question
    out = svc.answer(session.id, "because")
    assert out["stored_for"] == q.item_id and out["answer_type"] == "other"


def test_session_survives_a_new_service(seeded, assistant):
    session, q = InterviewService(seeded, assistant).start("ravi")
    restarted = InterviewService(seeded, assistant)  # e.g. another worker or a restart
    assert restarted.get(session.id).current == q
    assert restarted.answer(session.id, "because")["stored_for"] == q.item_id


def test_concurrent_save_is_rejected(seeded, assistant):
    import pytest
    from knowledge_transfer.errors import InvalidState
    svc = InterviewService(seeded, assistant)
    session, _ = svc.start("ravi")
    stale = svc.get(session.id)
    svc.skip(session.id)
    with pytest.raises(InvalidState):
        svc._save(stale)
