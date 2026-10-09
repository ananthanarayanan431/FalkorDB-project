"""Per-receiver handover plans.

plan = (what the leaver knew) - (what the receiver already knows), ordered by
PREREQUISITE_OF edges. The receiver's seniority picks the strategy:

  junior  everything they do not know, plus every prerequisite they are missing,
          foundations first, with documents as reading.
  mid/senior  only the delta that is not in a document: undocumented items and the
          interview answers (reasons, traps). Documented items they lack become
          one-line reading pointers.
"""
from knowledge_transfer.core.errors import NotFound
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.services.assistant import Assistant
from knowledge_transfer.services.gaps import gap_from_state

KNOWN_LEVEL = 2  # KNOWS level at or above this counts as already known


def _toposort(ids: list[str], edges: list[tuple[str, str]], priority) -> list[str]:
    """Prerequisites first; `priority(id)` breaks ties (lower goes first)."""
    indeg = {i: 0 for i in ids}
    out: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in edges:
        out[a].append(b)
        indeg[b] += 1
    ready = sorted((i for i in ids if indeg[i] == 0), key=priority)
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
        ready.sort(key=priority)
    order += [i for i in ids if i not in order]  # only reached on a prerequisite cycle
    return order


def _descendants(ids: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    out: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in edges:
        out[a].append(b)

    def count(start: str) -> int:
        seen: set[str] = set()
        stack = list(out[start])
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(out[n])
        return len(seen)

    return {i: count(i) for i in ids}


async def build_plan(graph: KnowledgeGraph, assistant: Assistant, leaver: str, receiver: str) -> dict:
    if await graph.person(leaver) is None:
        raise NotFound(f"Unknown person {leaver!r}")
    person = await graph.person(receiver)
    if person is None:
        raise NotFound(f"Unknown person {receiver!r}")
    junior = person["seniority"] == "junior"
    known = {i for i, lvl in (await graph.knows(receiver)).items() if lvl >= KNOWN_LEVEL}

    states = {s.id: s for s in await graph.leaver_items(leaver)}
    delta = [i for i in states if i not in known]
    if junior:
        wanted = [i for i in await graph.with_prerequisites(delta) if i not in known]
    else:
        wanted = delta

    answers = await graph.answers_for(wanted)
    docs = await graph.documents_for(wanted)
    details = await graph.items_by_id(wanted)

    steps_meta: dict[str, dict] = {}
    for i in wanted:
        s = states.get(i)
        has_answers, has_docs = bool(answers.get(i)), bool(docs.get(i))
        risk = gap_from_state(s).risk if s else 0
        # Documented items with no interview answer are reading; the rest is
        # knowledge that only exists in the leaver's head.
        mode = "read" if has_docs and not has_answers else "learn"
        steps_meta[i] = {"mode": mode, "risk": risk}

    ids = list(steps_meta)
    edges = await graph.prerequisite_edges(ids)
    if junior:
        # Most foundational first: the more steps build on an item, the earlier it goes.
        reach = _descendants(ids, edges)
        priority = lambda i: (-reach[i], details[i]["name"])  # noqa: E731
    else:
        priority = lambda i: (-steps_meta[i]["risk"], details[i]["name"])  # noqa: E731
    order = _toposort(ids, edges, priority)
    prereqs: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in edges:
        prereqs[b].append(details[a]["name"])

    steps = []
    for n, i in enumerate(order, 1):
        d, meta = details[i], steps_meta[i]
        steps.append({
            "order": n,
            "item_id": i,
            "name": d["name"],
            "kind": d["kind"],
            "mode": meta["mode"],
            "why_included": _why(i in states, meta["mode"]),
            "description": d["description"],
            "knowledge": answers.get(i, []),
            "read": docs.get(i, []),
            "learn_first": prereqs[i],
            "risk": meta["risk"],
        })

    style = (
        "Foundations first, each step builds on the previous one."
        if junior else "Only what you do not already know and cannot find in the docs."
    )
    summary = await assistant.summarise_plan(
        person["name"], person["seniority"], style, [s["name"] for s in steps]
    )
    return {
        "receiver": {k: person[k] for k in ("id", "name", "role", "seniority")},
        "leaver": leaver,
        "strategy": "foundations-first" if junior else "delta-only",
        "summary": summary,
        "skipped_already_known": len([i for i in states if i in known]),
        "steps": steps,
    }


def _why(leaver_touched: bool, mode: str) -> str:
    if not leaver_touched:
        return "prerequisite you need before the later steps"
    if mode == "read":
        return "documented; read it, no interview time needed"
    return "the leaver's knowledge you do not have yet"
