import pytest
from fakes import FakeLLM

from knowledge_transfer import gaps
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.errors import InvalidState, NotFound
from knowledge_transfer.interview import InterviewService
from knowledge_transfer.models import AnswerAnalysis, ExtractedItem


async def test_first_question_targets_highest_risk_open_gap(seeded, interviews):
    _, q = await interviews.start("ravi")
    top = (await gaps.open_gaps(seeded, "ravi"))[0]
    assert q.item_id == top.item_id
    assert "only person" in q.text and q.reasons == top.reasons


async def test_answer_is_stored_and_closes_the_gap(seeded, interviews):
    session, q = await interviews.start("ravi")
    out = await interviews.answer(session.id, "Gateway rate-limit window is 30 min; 40 gives margin.")
    assert out["stored_for"] == q.item_id
    assert out["next_question"]["item_id"] != q.item_id
    assert (await seeded.answers_for([q.item_id]))[q.item_id][0]["source"] == "interview"


async def test_interview_ends_when_no_open_gaps(seeded, interviews):
    session, q = await interviews.start("ravi")
    n = 0
    while q is not None and n < 50:
        await interviews.answer(session.id, "because")
        q = (await interviews.get(session.id)).current
        n += 1
    assert (await gaps.coverage(seeded, "ravi"))["percent"] == 100.0
    assert (await interviews.get(session.id)).status == "completed"


async def test_skip_does_not_repeat_the_question(interviews):
    session, q = await interviews.start("ravi")
    nxt = (await interviews.skip(session.id))["next_question"]
    assert nxt["item_id"] != q.item_id


async def test_transcript_records_answers_and_skips(interviews):
    session, q1 = await interviews.start("ravi")
    await interviews.answer(session.id, "because")
    q2 = (await interviews.get(session.id)).current
    await interviews.skip(session.id)
    turns = await interviews.transcript(session.id)
    assert [(t["seq"], t["action"], t["item_id"]) for t in turns] == [
        (1, "answer", q1.item_id), (2, "skip", q2.item_id),
    ]
    assert turns[0]["answer"] == "because" and turns[1]["answer"] is None


async def test_llm_answer_creates_new_gap_and_follow_up(seeded, store):
    analysis = AnswerAnalysis(
        answer_type="trap",
        items=[ExtractedItem(name="Nightly cron host", kind="system", depends_on=["Ledger sync job"])],
        follow_up="Who has access to the cron host?",
    )
    llm = FakeLLM({AnswerAnalysis: analysis}, text="LLM question?")
    svc = InterviewService(seeded, Assistant(llm), store)
    session, q = await svc.start("ravi")
    assert q.text == "LLM question?"
    out = await svc.answer(session.id, "It also needs the cron host restarted manually.")
    assert out["new_items"] == ["nightly-cron-host"]
    assert out["answer_type"] == "trap"
    assert out["next_question"]["is_follow_up"] and out["next_question"]["item_id"] == q.item_id
    assert "nightly-cron-host" in {g.item_id for g in await gaps.open_gaps(seeded, "ravi")}


async def test_unknown_leaver(graph, assistant, store):
    with pytest.raises(NotFound):
        await InterviewService(graph, assistant, store).start("nobody")


async def test_llm_failure_falls_back_to_templates(seeded, store):
    class BrokenLLM:
        async def ainvoke(self, _msgs):
            raise ConnectionError("provider down")

        def with_structured_output(self, _schema):
            return self

    svc = InterviewService(seeded, Assistant(BrokenLLM()), store)
    session, q = await svc.start("ravi")
    assert "only person" in q.text  # template question
    out = await svc.answer(session.id, "because")
    assert out["stored_for"] == q.item_id and out["answer_type"] == "other"


async def test_session_survives_a_new_service(seeded, assistant, store, interviews):
    session, q = await interviews.start("ravi")
    restarted = InterviewService(seeded, assistant, store)  # e.g. another worker or a restart
    assert (await restarted.get(session.id)).current == q
    assert (await restarted.answer(session.id, "because"))["stored_for"] == q.item_id


async def test_concurrent_save_is_rejected(interviews):
    session, _ = await interviews.start("ravi")
    stale = await interviews.get(session.id)
    await interviews.skip(session.id)
    with pytest.raises(InvalidState):
        await interviews._save(stale)
