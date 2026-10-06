"""Thin wrapper around FalkorDB: stores facts as (Entity)-[RELATION]->(Entity)."""
import logging
import os
import re
import time
from typing import Callable

from falkordb import FalkorDB
from redis.exceptions import ResponseError

logger = logging.getLogger(__name__)


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


# Relations that hold one value per subject. A new value replaces the old one,
# so "I moved to Paris" retires "lives in London". Other relations (likes, knows,
# ...) can have many values and are never replaced.
SINGLE_VALUED = {"LIVES_IN", "LIVES_AT", "WORKS_AT", "LOCATED_IN", "HAS_AGE", "IS_NAMED"}


# Entities closer than this (cosine distance, lower = more similar) count as a match.
SIMILARITY_MAX_DISTANCE = 0.45


class GraphStore:
    """`embed` maps a list of strings to a list of vectors. Without it the store
    still works, but entity lookup is exact-name only (no vector search)."""

    def __init__(
        self,
        db=None,
        graph_name: str | None = None,
        embed: Callable[[list[str]], list[list[float]]] | None = None,
        embedding_dim: int | None = None,
    ):
        self.embed = embed
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
        if self.embed:
            dim = embedding_dim or int(os.getenv("EMBEDDING_DIM", "1536"))
            try:
                self.graph.query(
                    "CREATE VECTOR INDEX FOR (e:Entity) ON (e.embedding) "
                    f"OPTIONS {{dimension: {dim}, similarityFunction: 'cosine'}}"
                )
            except ResponseError:
                self._check_index_dim(dim)  # index already exists

    def _check_index_dim(self, dim: int) -> None:
        """Fail early if the persisted vector index was built for another dimension."""
        rows = self.graph.ro_query("CALL db.indexes()").result_set
        for row in rows:
            opts = (row[3] or {}).get("embedding") if row[0] == "Entity" else None
            existing = opts.get("dimension") if opts else None
            if existing is not None and existing != dim:
                raise RuntimeError(
                    f"Vector index on Entity.embedding has dimension {existing} but "
                    f"the embedder is configured for {dim} (EMBEDDING_DIM). Set "
                    "EMBEDDING_DIM to match, or clear the graph with /reset and restart."
                )

    def add_fact(self, subject: str, relation: str, obj: str) -> None:
        s, o = _norm(subject), _norm(obj)
        if not s or not o:
            return
        rel = _rel_type(relation)
        if rel in SINGLE_VALUED:
            self.graph.query(
                f"MATCH (:Entity {{name: $s}})-[r:{rel}]->(b:Entity) "
                "WHERE b.name <> $o DELETE r",
                {"s": s, "o": o},
            )
        # created_at is set once; updated_at moves every time the fact is restated.
        now = int(time.time() * 1000)
        self.graph.query(
            "MERGE (a:Entity {name: $s}) "
            "MERGE (b:Entity {name: $o}) "
            f"MERGE (a)-[r:{rel}]->(b) "
            "ON CREATE SET r.created_at = $now "
            "SET r.updated_at = $now",
            {"s": s, "o": o, "now": now},
        )
        try:
            self._embed_missing([s, o])
        except Exception:
            # The fact is already stored; missing vectors are backfilled by the
            # next add_fact that touches these entities.
            logger.warning("Embedding failed for %s, %s", s, o, exc_info=True)

    def _embed_missing(self, names: list[str]) -> None:
        if not self.embed:
            return
        have = self.graph.ro_query(
            "MATCH (e:Entity) WHERE e.name IN $names AND e.embedding IS NOT NULL "
            "RETURN e.name",
            {"names": names},
        )
        done = {row[0] for row in have.result_set}
        todo = [n for n in dict.fromkeys(names) if n not in done]
        if not todo:
            return
        for name, vec in zip(todo, self.embed(todo), strict=True):
            self.graph.query(
                "MATCH (e:Entity {name: $n}) SET e.embedding = vecf32($v)",
                {"n": name, "v": vec},
            )

    def similar_entities(self, names: list[str], k: int = 3) -> list[str]:
        """Entity names close in meaning to `names`, e.g. "puppy" -> "dog"."""
        names = [_norm(n) for n in names if n and n.strip()]
        if not self.embed or not names:
            return []
        found: list[str] = []
        try:
            vectors = self.embed(names)
        except Exception:
            logger.warning("Embedding failed during entity lookup", exc_info=True)
            return []
        for vec in vectors:
            result = self.graph.ro_query(
                "CALL db.idx.vector.queryNodes('Entity', 'embedding', $k, vecf32($v)) "
                "YIELD node, score WHERE score <= $max RETURN node.name",
                {"k": k, "v": vec, "max": SIMILARITY_MAX_DISTANCE},
            )
            found += [row[0] for row in result.result_set if row[0] not in found]
        return found

    def facts_about(
        self, names: list[str], fallback: list[str] | None = None, limit: int = 50
    ) -> list[str]:
        """Facts within two hops of `names`, as 'a RELATION b' strings.

        Facts about `names` come first. `fallback` entities (for example "user")
        only fill whatever room is left under `limit`, so a well-connected
        fallback entity cannot crowd out facts about the current topic.
        """
        facts = self._facts_near(names + self.similar_entities(names), limit)
        if fallback and len(facts) < limit:
            for fact in self._facts_near(fallback, limit):
                if fact not in facts:
                    facts.append(fact)
                if len(facts) >= limit:
                    break
        return facts

    def _facts_near(self, names: list[str], limit: int) -> list[str]:
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

    def profile_retrieval(self, names: list[str]) -> str:
        """Execution plan with per-step timings for the retrieval query."""
        plan = self.graph.profile(
            "MATCH (e:Entity) WHERE e.name IN $names "
            "MATCH p = (e)-[*1..2]-(:Entity) "
            "UNWIND relationships(p) AS r "
            "RETURN DISTINCT startNode(r).name, type(r), endNode(r).name LIMIT 50",
            {"names": [_norm(n) for n in names]},
        )
        return str(plan)

    def reset(self) -> None:
        self.graph.query("MATCH (n) DETACH DELETE n")