from fakes.llm import FakeLLM

from knowledge_transfer.schemas import ExtractedItem, Extraction
from knowledge_transfer.services import gaps, handover
from knowledge_transfer.services.assistant import Assistant
from knowledge_transfer.services.ingest import ingest_braindump


def names(plan):
    return [s["name"] for s in plan["steps"]]


async def test_plans_differ_per_receiver(seeded, assistant):
    mid = await handover.build_plan(seeded, assistant, "ravi", "priya")
    junior = await handover.build_plan(seeded, assistant, "ravi", "sam")
    assert mid["strategy"] == "delta-only" and junior["strategy"] == "foundations-first"
    # Priya already knows the billing service and domain basics; Sam does not.
    assert "Billing service" not in names(mid) and "Billing service" in names(junior)
    assert "Payments domain basics" not in names(mid) and "Payments domain basics" in names(junior)
    assert len(junior["steps"]) > len(mid["steps"])


async def test_junior_plan_respects_prerequisites(seeded, assistant):
    plan = await handover.build_plan(seeded, assistant, "ravi", "sam")
    pos = {s["item_id"]: s["order"] for s in plan["steps"]}
    for a, b in await seeded.prerequisite_edges(list(pos)):
        assert pos[a] < pos[b], f"{a} must come before {b}"
    assert plan["steps"][0]["name"] == "Payments domain basics"


async def test_mid_plan_only_undocumented_knowledge(seeded, assistant):
    plan = await handover.build_plan(seeded, assistant, "ravi", "priya")
    assert all(s["mode"] == "learn" for s in plan["steps"])
    assert "Month-end close procedure" in names(plan)


async def test_documented_items_become_reading_for_junior(seeded, assistant):
    plan = await handover.build_plan(seeded, assistant, "ravi", "sam")
    runbook = next(s for s in plan["steps"] if s["item_id"] == "on-call-runbook")
    assert runbook["mode"] == "read" and runbook["read"] == ["Payments on-call runbook"]


async def test_interview_answers_travel_with_the_plan(seeded, assistant):
    await seeded.add_answer("retry-wait-40-minutes", "ravi", "q", "Gateway blocks retries inside 30 min.", "rationale")
    for who in ("priya", "sam"):
        plan = await handover.build_plan(seeded, assistant, "ravi", who)
        step = next(s for s in plan["steps"] if s["item_id"] == "retry-wait-40-minutes")
        assert step["knowledge"][0]["text"].startswith("Gateway blocks")
        assert step["knowledge"][0]["source"] == "interview"


async def test_known_items_are_removed(seeded, assistant):
    await seeded.set_knows("priya", "month-end-close", 3)
    plan = await handover.build_plan(seeded, assistant, "ravi", "priya")
    assert "Month-end close procedure" not in names(plan)


async def test_braindump_mode_works_without_sources(graph):
    extraction = Extraction(items=[
        ExtractedItem(name="Pager rota", kind="topic", owned=True),
        ExtractedItem(name="Alert router", kind="system", depends_on=["Pager rota"]),
    ])
    await graph.upsert_person("ravi", "Ravi", status="leaving", seniority="senior")
    out = await ingest_braindump(graph, Assistant(FakeLLM({Extraction: extraction})), "ravi", "I own the pager rota...")
    assert set(out["new_items"]) == {"pager-rota", "alert-router"}
    assert {g.item_id for g in await gaps.open_gaps(graph, "ravi")} == {"pager-rota", "alert-router"}


async def test_braindump_merges_with_sources(seeded):
    extraction = Extraction(items=[ExtractedItem(name="Billing retry scheduler", owned=True,
                                                 depends_on=["Cron host"])])
    out = await ingest_braindump(seeded, Assistant(FakeLLM({Extraction: extraction})), "ravi", "...")
    assert out["new_items"] == ["cron-host"]  # existing item merged, not duplicated
