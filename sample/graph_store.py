"""Thin wrapper around FalkorDB: stores facts as (Entity)-[RELATION]->(Entity)."""
import os
import re

from falkordb import FalkorDB
from redis.exceptions import ResponseError


def _norm(name: str) -> str:
    return " ".join(name.lower().split())


def _rel_type(relation: str) -> str:
    # Relationship types cannot be passed as query parameters in Cypher,
    # so the string is restricted to [A-Z0-9_] before it is put into the query.
    rel = re.sub(r"[^A-Za-z0-9]+", "_", relation).strip("_").upper()
    if not rel:
        rel = "RELATED_TO"
    if rel[0].isdigit():
        rel = "R_" + rel
    return rel


class GraphStore:
    def __init__(self, db=None, graph_name: str | None = None):
        self.db = db or FalkorDB(
            host=os.getenv("FALKORDB_HOST", "localhost"),
            port=int(os.getenv("FALKORDB_PORT", "6379")),
        )
        self.graph = self.db.select_graph(
            graph_name or os.getenv("FALKORDB_GRAPH", "chat_memory")
        )
        try:
            self.graph.query("CREATE INDEX FOR (e:Entity) ON (e.name)")
        except ResponseError:
            pass  # index already exists

    def add_fact(self, subject: str, relation: str, obj: str) -> None:
        s, o = _norm(subject), _norm(obj)
        if not s or not o:
            return
        self.graph.query(
            "MERGE (a:Entity {name: $s}) "
            "MERGE (b:Entity {name: $o}) "
            f"MERGE (a)-[:{_rel_type(relation)}]->(b)",
            {"s": s, "o": o},
        )

    def facts_about(self, names: list[str], limit: int = 50) -> list[str]:
        """Facts within two hops of the given entities, as 'a RELATION b' strings."""
        names = [_norm(n) for n in names if n and n.strip()]
        if not names:
            return []
        result = self.graph.ro_query(
            "MATCH (e:Entity) WHERE e.name IN $names "
            "MATCH p = (e)-[*1..2]-(:Entity) "
            "UNWIND relationships(p) AS r "
            "RETURN DISTINCT startNode(r).name, type(r), endNode(r).name "
            "LIMIT $limit",
            {"names": names, "limit": limit},
        )
        return [f"{a} {rel} {b}" for a, rel, b in result.result_set]

    def all_facts(self, limit: int = 200) -> list[str]:
        result = self.graph.ro_query(
            "MATCH (a:Entity)-[r]->(b:Entity) "
            "RETURN a.name, type(r), b.name LIMIT $limit",
            {"limit": limit},
        )
        return [f"{a} {rel} {b}" for a, rel, b in result.result_set]

    def reset(self) -> None:
        self.graph.query("MATCH (n) DETACH DELETE n")