"""Gap analysis: what does the leaver know that nobody else does?

A knowledge item is *unique* to the leaver when no one else touched it
(`sole_owner`) or no document covers it (`undocumented`). A unique item is a
*gap* until an interview answer explains it. Risk ranks gaps by how much would
break: dependents, plus extra weight for sole ownership and missing docs.
"""
from dataclasses import asdict, dataclass

from knowledge_transfer.graph import ItemState, KnowledgeGraph


@dataclass
class Gap:
    item_id: str
    name: str
    kind: str
    description: str
    sole_owner: bool
    undocumented: bool
    dependents: int
    answers: int
    risk: int
    reasons: list[str]

    @property
    def unique(self) -> bool:
        return self.sole_owner or self.undocumented

    @property
    def open(self) -> bool:
        return self.unique and self.answers == 0

    def to_dict(self):
        d = asdict(self)
        d["open"] = self.open
        return d


def gap_from_state(s: ItemState) -> Gap:
    sole, undoc = s.other_people == 0, s.documents == 0
    reasons = []
    if sole:
        reasons.append("only the leaver worked on it")
    if undoc:
        reasons.append("no documentation")
    if s.dependents:
        reasons.append(f"{s.dependents} other item(s) depend on it")
    risk = s.dependents + (2 if sole else 0) + (2 if undoc else 0)
    return Gap(s.id, s.name, s.kind, s.description, sole, undoc, s.dependents,
               s.answers, risk, reasons)


def analyse(graph: KnowledgeGraph, leaver: str) -> list[Gap]:
    """All unique items of the leaver, highest risk first (open gaps before covered)."""
    gaps = [g for g in map(gap_from_state,graph.leaver_items(leaver)) if g.unique]
    return sorted(gaps, key=lambda g: (not g.open, -g.risk, g.name))


def open_gaps(graph: KnowledgeGraph, leaver: str) -> list[Gap]:
    return [g for g in analyse(graph, leaver) if g.open]


def coverage(graph: KnowledgeGraph, leaver: str) -> dict:
    gaps = analyse(graph, leaver)
    covered = [g for g in gaps if not g.open]
    total_risk = sum(g.risk for g in gaps) or 1
    return {
        "leaver": leaver,
        "unique_items": len(gaps),
        "covered": len(covered),
        "open": len(gaps) - len(covered),
        "percent": round(100 * len(covered) / len(gaps), 1) if gaps else 100.0,
        "risk_weighted_percent": round(100 * sum(g.risk for g in covered) / total_risk, 1),
        "items": [g.to_dict() for g in gaps],
    }
