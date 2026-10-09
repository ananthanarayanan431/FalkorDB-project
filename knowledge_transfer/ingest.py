"""Both input modes write the same schema.

Mode A (`ingest_sources`): structured company data (tickets, docs, code ownership).
Mode B (`ingest_braindump`): free text from the leaver, turned into items by an LLM.
Either can run first, or both; items are merged by id.
"""
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.models import Extraction, SourceBundle, slug


def ingest_sources(graph: KnowledgeGraph, bundle: SourceBundle) -> dict:
    for p in bundle.people:
        graph.upsert_person(p.id, p.name, p.role, p.seniority, p.status)
    for i in bundle.items:
        graph.upsert_item(i.id, i.name, i.kind, i.description, source="doc")
    for d in bundle.documents:
        graph.upsert_document(d.id, d.title, d.covers)
    for c in bundle.contributions:
        graph.link_touch(c.person, c.item, c.rel, c.source, c.ref)
    for link in bundle.links:
        graph.link_items(link.src, link.rel, link.dst)
    for k in bundle.knows:
        graph.set_knows(k.person, k.item, k.level)
    return {
        "people": len(bundle.people), "items": len(bundle.items),
        "documents": len(bundle.documents), "contributions": len(bundle.contributions),
        "links": len(bundle.links), "knows": len(bundle.knows),
    }


def apply_extraction(graph: KnowledgeGraph, person: str, extraction: Extraction,
                     source: str, ref: str = "", confidence: float = 0.7) -> list[str]:
    """Write LLM-extracted items. Returns the ids of items that did not exist before."""
    created: list[str] = []
    for it in extraction.items:
        id = slug(it.name)
        if not id:
            continue
        if graph.item(id) is None:
            created.append(id)
        graph.upsert_item(id, it.name, it.kind, it.description, source, ref, confidence)
        graph.link_touch(person, id, "OWNS" if it.owned else "WORKED_ON", source, ref, confidence)
        for dep in it.depends_on:
            if dep_id := slug(dep):
                if graph.item(dep_id) is None:
                    graph.upsert_item(dep_id, dep, "topic", "", source, ref, confidence)
                    created.append(dep_id)
                graph.link_items(id, "DEPENDS_ON", dep_id, source, ref, confidence)
        for pre in it.prerequisites:
            if pre_id := slug(pre):
                if graph.item(pre_id) is None:
                    graph.upsert_item(pre_id, pre, "topic", "", source, ref, confidence)
                    created.append(pre_id)
                graph.link_items(pre_id, "PREREQUISITE_OF", id, source, ref, confidence)
    return created


def ingest_braindump(graph: KnowledgeGraph, assistant, person: str, text: str) -> dict:
    extraction = assistant.extract_braindump(text)
    created = apply_extraction(graph, person, extraction, "braindump")
    return {"items_found": len(extraction.items), "new_items": created}
