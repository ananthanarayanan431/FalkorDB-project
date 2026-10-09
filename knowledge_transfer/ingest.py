"""Both input modes write the same schema.

Mode A (`ingest_sources`): structured company data (tickets, docs, code ownership).
Mode B (`ingest_braindump`): free text from the leaver, turned into items by an LLM.
Either can run first, or both; items are merged by id.
"""
from knowledge_transfer.errors import InvalidInput
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.models import Extraction, SourceBundle, slug


async def unknown_references(graph: KnowledgeGraph, bundle: SourceBundle) -> list[dict]:
    """References to people or items that are neither in the bundle nor in the graph.
    Edges to them would be silently dropped by the MATCH in each write."""
    people = {p.id for p in bundle.people}
    items = {i.id for i in bundle.items}
    refs: list[tuple[str, str, str]] = []  # (field, kind, id)
    for n, d in enumerate(bundle.documents):
        refs += [(f"documents[{n}].covers", "item", i) for i in d.covers]
    for n, c in enumerate(bundle.contributions):
        refs += [(f"contributions[{n}].person", "person", c.person),
                 (f"contributions[{n}].item", "item", c.item)]
    for n, link in enumerate(bundle.links):
        refs += [(f"links[{n}].src", "item", link.src), (f"links[{n}].dst", "item", link.dst)]
    for n, k in enumerate(bundle.knows):
        refs += [(f"knows[{n}].person", "person", k.person), (f"knows[{n}].item", "item", k.item)]

    exists: dict[tuple[str, str], bool] = {}
    missing = []
    for field, kind, id in refs:
        if id in (people if kind == "person" else items):
            continue
        if (kind, id) not in exists:
            lookup = graph.person if kind == "person" else graph.item
            exists[kind, id] = await lookup(id) is not None
        if not exists[kind, id]:
            missing.append({"field": field, "message": f"unknown {kind} {id!r}"})
    return missing


async def ingest_sources(graph: KnowledgeGraph, bundle: SourceBundle) -> dict:
    if missing := await unknown_references(graph, bundle):
        raise InvalidInput(f"Bundle references {len(missing)} unknown id(s); nothing was written", missing)
    for p in bundle.people:
        await graph.upsert_person(p.id, p.name, p.role, p.seniority, p.status)
    for i in bundle.items:
        await graph.upsert_item(i.id, i.name, i.kind, i.description, source="doc")
    for d in bundle.documents:
        await graph.upsert_document(d.id, d.title, d.covers)
    for c in bundle.contributions:
        await graph.link_touch(c.person, c.item, c.rel, c.source, c.ref)
    for link in bundle.links:
        await graph.link_items(link.src, link.rel, link.dst)
    for k in bundle.knows:
        await graph.set_knows(k.person, k.item, k.level)
    return {
        "people": len(bundle.people), "items": len(bundle.items),
        "documents": len(bundle.documents), "contributions": len(bundle.contributions),
        "links": len(bundle.links), "knows": len(bundle.knows),
    }


async def apply_extraction(graph: KnowledgeGraph, person: str, extraction: Extraction,
                     source: str, ref: str = "", confidence: float = 0.7) -> list[str]:
    """Write LLM-extracted items. Returns the ids of items that did not exist before."""
    created: list[str] = []
    for it in extraction.items:
        id = slug(it.name)
        if not id:
            continue
        if await graph.item(id) is None:
            created.append(id)
        await graph.upsert_item(id, it.name, it.kind, it.description, source, ref, confidence)
        await graph.link_touch(person, id, "OWNS" if it.owned else "WORKED_ON", source, ref, confidence)
        for dep in it.depends_on:
            if dep_id := slug(dep):
                if await graph.item(dep_id) is None:
                    await graph.upsert_item(dep_id, dep, "topic", "", source, ref, confidence)
                    created.append(dep_id)
                await graph.link_items(id, "DEPENDS_ON", dep_id, source, ref, confidence)
        for pre in it.prerequisites:
            if pre_id := slug(pre):
                if await graph.item(pre_id) is None:
                    await graph.upsert_item(pre_id, pre, "topic", "", source, ref, confidence)
                    created.append(pre_id)
                await graph.link_items(pre_id, "PREREQUISITE_OF", id, source, ref, confidence)
    return created


async def ingest_braindump(graph: KnowledgeGraph, assistant, person: str, text: str) -> dict:
    extraction = await assistant.extract_braindump(text)
    created = await apply_extraction(graph, person, extraction, "braindump")
    return {"items_found": len(extraction.items), "new_items": created}
