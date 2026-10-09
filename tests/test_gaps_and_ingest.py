from knowledge_transfer import gaps
from knowledge_transfer.ingest import ingest_sources
from knowledge_transfer.seed.northwind import BUNDLE


def test_seed_ingest_is_idempotent(graph):
    ingest_sources(graph, BUNDLE)
    first = graph.export()
    ingest_sources(graph, BUNDLE)
    again = graph.export()
    assert len(first["nodes"]) == len(again["nodes"])
    assert len(first["edges"]) == len(again["edges"])


def test_gaps_are_what_only_the_leaver_knows(seeded):
    open_ids = {g.item_id for g in gaps.open_gaps(seeded, "ravi")}
    assert {"billing-retry-scheduler", "retry-wait-40-minutes", "ledger-sync-job",
            "reconciliation-batch", "month-end-close"} <= open_ids
    # documented and shared with others: not a gap
    assert "on-call-runbook" not in open_ids
    # documented, but only Ravi touched... still has doc and Priya touched it
    assert "billing-service" not in open_ids


def test_gaps_ranked_by_risk(seeded):
    found = gaps.open_gaps(seeded, "ravi")
    risks = [g.risk for g in found]
    assert risks == sorted(risks, reverse=True)
    assert found[0].item_id == "billing-retry-scheduler" or found[0].dependents >= 1


def test_answer_closes_gap_and_raises_coverage(seeded):
    before = gaps.coverage(seeded, "ravi")
    seeded.add_answer("ledger-sync-job", "ravi", "q", "Runs at 2am to avoid the gateway payout window")
    after = gaps.coverage(seeded, "ravi")
    assert after["covered"] == before["covered"] + 1
    assert after["percent"] > before["percent"]
    assert "ledger-sync-job" not in {g.item_id for g in gaps.open_gaps(seeded, "ravi")}


def test_provenance_recorded(seeded):
    seeded.add_answer("ledger-sync-job", "ravi", "q", "a")
    a = seeded.answers_for(["ledger-sync-job"])["ledger-sync-job"][0]
    assert a["source"] == "interview" and a["created_at"]
