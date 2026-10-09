"""FalkorDB access for the knowledge-transfer graph.

Schema
  (:Person {id, name, role, seniority, status})
  (:Item:System|Decision|Topic {id, name, kind, description})
  (:Document {id, title})
  (:Answer {id, text, question, kind})
  (Person)-[:OWNS|WORKED_ON|AUTHORED]->(Item)      who touched what
  (Person)-[:KNOWS {level}]->(Item)                what a receiver already knows
  (Item)-[:DEPENDS_ON]->(Item)
  (Item)-[:PREREQUISITE_OF]->(Item)                learn the source before the target
  (Item)-[:DOCUMENTED_BY]->(Document)
  (Answer)-[:EXPLAINS]->(Item), (Person)-[:GAVE]->(Answer)

Every node and edge written here carries provenance: source, source_ref,
confidence, created_at.
"""
import os
import time
import uuid
from dataclasses import dataclass

from falkordb import FalkorDB
from redis.exceptions import ResponseError

LABELS = {"system": "System", "decision": "Decision", "topic": "Topic"}
TOUCH_RELS = {"OWNS", "WORKED_ON", "AUTHORED"}
LINK_RELS = {"DEPENDS_ON", "PREREQUISITE_OF"}


def _now() -> int:
    return int(time.time() * 1000)


@dataclass
class ItemState:
    """One thing the leaver touched, with the facts the gap analysis needs."""
    id: str
    name: str
    kind: str
    description: str
    other_people: int  # other people with OWNS/WORKED_ON/AUTHORED on it
    documents: int
    answers: int
    dependents: int  # items that directly depend on it


class KnowledgeGraph:
    def __init__(self, db=None, graph_name: str | None = None):
        self.db = db or FalkorDB(
            host=os.getenv("FALKORDB_HOST", "localhost"),
            port=int(os.getenv("FALKORDB_PORT", "6379")),
        )
        self.graph = self.db.select_graph(
            graph_name or os.getenv("FALKORDB_KT_GRAPH", "knowledge_transfer")
        )
        for label in ("Person", "Item", "Document", "Answer"):
            try:
                self.graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
            except ResponseError:
                pass  # index already exists

    # ---- writes -----------------------------------------------------------

    def upsert_person(self, id, name, role="", seniority="mid", status="active"):
        self.graph.query(
            "MERGE (p:Person {id: $id}) "
            "SET p.name = $name, p.role = $role, p.seniority = $seniority, p.status = $status",
            {"id": id, "name": name, "role": role, "seniority": seniority, "status": status},
        )

    def upsert_item(self, id, name, kind="topic", description="",
                    source="doc", source_ref="", confidence=1.0):
        label = LABELS[kind]
        self.graph.query(
            "MERGE (i:Item {id: $id}) "
            "ON CREATE SET i.source = $source, i.source_ref = $ref, "
            "i.confidence = $conf, i.created_at = $now "
            f"SET i:{label}, i.name = $name, i.kind = $kind, "
            "i.description = CASE WHEN $desc <> '' THEN $desc "
            "ELSE coalesce(i.description, '') END",
            {"id": id, "name": name, "kind": kind, "desc": description,
             "source": source, "ref": source_ref, "conf": confidence, "now": _now()},
        )

    def upsert_document(self, id, title, covers=(), source="doc"):
        self.graph.query(
            "MERGE (d:Document {id: $id}) SET d.title = $title, d.source = $source",
            {"id": id, "title": title, "source": source},
        )
        for item in covers:
            self.graph.query(
                "MATCH (i:Item {id: $item}), (d:Document {id: $doc}) "
                "MERGE (i)-[r:DOCUMENTED_BY]->(d) "
                "ON CREATE SET r.source = $source, r.created_at = $now",
                {"item": item, "doc": id, "source": source, "now": _now()},
            )

    def link_touch(self, person, item, rel="WORKED_ON", source="ticket", ref="", confidence=1.0):
        assert rel in TOUCH_RELS, rel
        self.graph.query(
            f"MATCH (p:Person {{id: $p}}), (i:Item {{id: $i}}) MERGE (p)-[r:{rel}]->(i) "
            "ON CREATE SET r.source = $source, r.source_ref = $ref, "
            "r.confidence = $conf, r.created_at = $now",
            {"p": person, "i": item, "source": source, "ref": ref,
             "conf": confidence, "now": _now()},
        )

    def link_items(self, src, rel, dst, source="doc", ref="", confidence=1.0):
        assert rel in LINK_RELS, rel
        self.graph.query(
            f"MATCH (a:Item {{id: $a}}), (b:Item {{id: $b}}) MERGE (a)-[r:{rel}]->(b) "
            "ON CREATE SET r.source = $source, r.source_ref = $ref, "
            "r.confidence = $conf, r.created_at = $now",
            {"a": src, "b": dst, "source": source, "ref": ref,
             "conf": confidence, "now": _now()},
        )

    def set_knows(self, person, item, level=2):
        self.graph.query(
            "MATCH (p:Person {id: $p}), (i:Item {id: $i}) MERGE (p)-[r:KNOWS]->(i) "
            "SET r.level = $level, r.source = 'profile', r.updated_at = $now",
            {"p": person, "i": item, "level": level, "now": _now()},
        )

    def add_answer(self, item, person, question, text, kind="other",
                   source="interview", confidence=0.8) -> str:
        id = uuid.uuid4().hex
        self.graph.query(
            "MATCH (i:Item {id: $item}), (p:Person {id: $person}) "
            "CREATE (a:Answer {id: $id, text: $text, question: $q, kind: $kind, "
            "source: $source, confidence: $conf, created_at: $now}) "
            "CREATE (a)-[:EXPLAINS {source: $source, created_at: $now}]->(i) "
            "CREATE (p)-[:GAVE]->(a)",
            {"item": item, "person": person, "id": id, "text": text, "q": question,
             "kind": kind, "source": source, "conf": confidence, "now": _now()},
        )
        return id

    def reset(self):
        self.graph.query("MATCH (n) DETACH DELETE n")

    # ---- reads ------------------------------------------------------------

    def person(self, id):
        rows = self.graph.ro_query(
            "MATCH (p:Person {id: $id}) RETURN p.id, p.name, p.role, p.seniority, p.status",
            {"id": id},
        ).result_set
        if not rows:
            return None
        return dict(zip(("id", "name", "role", "seniority", "status"), rows[0]))

    def leaving_person(self):
        rows = self.graph.ro_query(
            "MATCH (p:Person {status: 'leaving'}) RETURN p.id ORDER BY p.id LIMIT 1"
        ).result_set
        return rows[0][0] if rows else None

    def item(self, id):
        rows = self.graph.ro_query(
            "MATCH (i:Item {id: $id}) RETURN i.id, i.name, i.kind, i.description",
            {"id": id},
        ).result_set
        if not rows:
            return None
        return dict(zip(("id", "name", "kind", "description"), rows[0]))

    def leaver_items(self, leaver) -> list[ItemState]:
        """Everything the leaver touched, with who else touched it, whether it is
        documented, how many interview answers explain it, and what depends on it."""
        rows = self.graph.ro_query(
            "MATCH (l:Person {id: $leaver})-[:OWNS|WORKED_ON|AUTHORED]->(i:Item) "
            "WITH DISTINCT i "
            "OPTIONAL MATCH (o:Person)-[:OWNS|WORKED_ON|AUTHORED]->(i) WHERE o.id <> $leaver "
            "WITH i, count(DISTINCT o) AS others "
            "OPTIONAL MATCH (i)-[:DOCUMENTED_BY]->(d:Document) "
            "WITH i, others, count(DISTINCT d) AS docs "
            "OPTIONAL MATCH (a:Answer)-[:EXPLAINS]->(i) "
            "WITH i, others, docs, count(DISTINCT a) AS answers "
            "OPTIONAL MATCH (x:Item)-[:DEPENDS_ON]->(i) "
            "RETURN i.id, i.name, i.kind, i.description, others, docs, answers, "
            "count(DISTINCT x)",
            {"leaver": leaver},
        ).result_set
        return [ItemState(*r) for r in rows]

    def related(self, item_id):
        """Neighbouring items and documents, used as context for questions."""
        r = self.graph.ro_query(
            "MATCH (i:Item {id: $id}) "
            "OPTIONAL MATCH (i)-[:DEPENDS_ON]->(dep:Item) "
            "OPTIONAL MATCH (user:Item)-[:DEPENDS_ON]->(i) "
            "OPTIONAL MATCH (i)-[:DOCUMENTED_BY]->(doc:Document) "
            "RETURN collect(DISTINCT dep.name), collect(DISTINCT user.name), "
            "collect(DISTINCT doc.title)",
            {"id": item_id},
        ).result_set[0]
        return {"depends_on": r[0], "used_by": r[1], "documents": r[2]}

    def knows(self, person) -> dict[str, int]:
        rows = self.graph.ro_query(
            "MATCH (:Person {id: $p})-[k:KNOWS]->(i:Item) RETURN i.id, k.level", {"p": person}
        ).result_set
        return {r[0]: r[1] for r in rows}

    def with_prerequisites(self, ids: list[str]) -> set[str]:
        """`ids` plus everything that must be understood first (transitively)."""
        rows = self.graph.ro_query(
            "MATCH (p:Item)-[:PREREQUISITE_OF*1..10]->(i:Item) WHERE i.id IN $ids "
            "RETURN DISTINCT p.id",
            {"ids": ids},
        ).result_set
        return set(ids) | {r[0] for r in rows}

    def prerequisite_edges(self, ids: list[str]) -> list[tuple[str, str]]:
        rows = self.graph.ro_query(
            "MATCH (a:Item)-[:PREREQUISITE_OF]->(b:Item) "
            "WHERE a.id IN $ids AND b.id IN $ids RETURN a.id, b.id",
            {"ids": ids},
        ).result_set
        return [(r[0], r[1]) for r in rows]

    def items_by_id(self, ids: list[str]) -> dict[str, dict]:
        rows = self.graph.ro_query(
            "MATCH (i:Item) WHERE i.id IN $ids RETURN i.id, i.name, i.kind, i.description",
            {"ids": ids},
        ).result_set
        return {r[0]: dict(zip(("id", "name", "kind", "description"), r)) for r in rows}

    def documents_for(self, ids: list[str]) -> dict[str, list[str]]:
        rows = self.graph.ro_query(
            "MATCH (i:Item)-[:DOCUMENTED_BY]->(d:Document) WHERE i.id IN $ids "
            "RETURN i.id, d.title",
            {"ids": ids},
        ).result_set
        out: dict[str, list[str]] = {}
        for item, title in rows:
            out.setdefault(item, []).append(title)
        return out

    def answers_for(self, ids: list[str]) -> dict[str, list[dict]]:
        rows = self.graph.ro_query(
            "MATCH (a:Answer)-[:EXPLAINS]->(i:Item) WHERE i.id IN $ids "
            "RETURN i.id, a.text, a.kind, a.source, a.created_at ORDER BY a.created_at",
            {"ids": ids},
        ).result_set
        out: dict[str, list[dict]] = {}
        for item, text, kind, source, ts in rows:
            out.setdefault(item, []).append(
                {"text": text, "kind": kind, "source": source, "created_at": ts}
            )
        return out

    def export(self):
        """Nodes and edges for a graph visualisation."""
        nodes = self.graph.ro_query(
            "MATCH (n) RETURN n.id, labels(n), coalesce(n.name, n.title, n.kind), n.status"
        ).result_set
        edges = self.graph.ro_query(
            "MATCH (a)-[r]->(b) RETURN a.id, type(r), b.id"
        ).result_set
        return {
            "nodes": [{"id": n[0], "labels": n[1], "name": n[2], "status": n[3]} for n in nodes],
            "edges": [{"src": e[0], "rel": e[1], "dst": e[2]} for e in edges],
        }
