from knowledge_transfer import gaps
from knowledge_transfer.ingest import ingest_sources
from knowledge_transfer.seed.northwind import BUNDLE


async def test_seed_ingest_is_idempotent(graph):
    await ingest_sources(graph, BUNDLE)
    first = await graph.export()
    await ingest_sources(graph, BUNDLE)
    again = await graph.export()
    assert len(first["nodes"]) == len(again["nodes"])
    assert len(first["edges"]) == len(again["edges"])


async def test_gaps_are_what_only_the_leaver_knows(seeded):
    open_ids = {g.item_id for g in await gaps.open_gaps(seeded, "ravi")}
    assert {"billing-retry-scheduler", "retry-wait-40-minutes", "ledger-sync-job",
            "reconciliation-batch", "month-end-close"} <= open_ids
    # documented and shared with others: not a gap
    assert "on-call-runbook" not in open_ids
    # documented, but only Ravi touched... still has doc and Priya touched it
    assert "billing-service" not in open_ids


async def test_gaps_ranked_by_risk(seeded):
    found = await gaps.open_gaps(seeded, "ravi")
    risks = [g.risk for g in found]
    assert risks == sorted(risks, reverse=True)
    assert found[0].item_id == "billing-retry-scheduler" or found[0].dependents >= 1


async def test_answer_closes_gap_and_raises_coverage(seeded):
    before = await gaps.coverage(seeded, "ravi")
    await seeded.add_answer("ledger-sync-job", "ravi", "q", "Runs at 2am to avoid the gateway payout window")
    after = await gaps.coverage(seeded, "ravi")
    assert after["covered"] == before["covered"] + 1
    assert after["percent"] > before["percent"]
    assert "ledger-sync-job" not in {g.item_id for g in await gaps.open_gaps(seeded, "ravi")}


async def test_provenance_recorded(seeded):
    await seeded.add_answer("ledger-sync-job", "ravi", "q", "a")
    a = (await seeded.answers_for(["ledger-sync-job"]))["ledger-sync-job"][0]
    assert a["source"] == "interview" and a["created_at"]
