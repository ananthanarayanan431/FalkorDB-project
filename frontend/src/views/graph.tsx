"use client";

import { useMemo, useState } from "react";

import { Badge, Button, Card, cx, EmptyState, ErrorAlert, inputClass, Loading, PageHeader, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { plural } from "@/lib/format";
import type { GraphExport, GraphNode } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

const NODE_TYPES = ["Person", "Item", "Document", "Answer"] as const;

function nodeType(n: GraphNode): string {
  return NODE_TYPES.find((t) => n.labels.includes(t)) ?? n.labels[0] ?? "Node";
}

function label(n: GraphNode | undefined, id: string): string {
  if (!n) return id;
  if (nodeType(n) === "Answer") return `Answer (${n.name ?? "other"})`;
  return n.name ?? n.id;
}

function Explorer({ data }: { data: GraphExport }) {
  const [type, setType] = useState<string>("Item");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const byId = useMemo(() => new Map(data.nodes.map((n) => [n.id, n])), [data]);
  const degree = useMemo(() => {
    const d = new Map<string, number>();
    for (const e of data.edges) {
      d.set(e.src, (d.get(e.src) ?? 0) + 1);
      d.set(e.dst, (d.get(e.dst) ?? 0) + 1);
    }
    return d;
  }, [data]);
  const relCounts = useMemo(() => {
    const c = new Map<string, number>();
    for (const e of data.edges) c.set(e.rel, (c.get(e.rel) ?? 0) + 1);
    return [...c.entries()].sort((a, b) => b[1] - a[1]);
  }, [data]);

  const q = query.trim().toLowerCase();
  const nodes = data.nodes
    .filter((n) => nodeType(n) === type)
    .filter((n) => !q || n.id.toLowerCase().includes(q) || (n.name ?? "").toLowerCase().includes(q))
    .sort((a, b) => label(a, a.id).localeCompare(label(b, b.id)));
  const sel = selected ? byId.get(selected) : undefined;
  const outgoing = selected ? data.edges.filter((e) => e.src === selected) : [];
  const incoming = selected ? data.edges.filter((e) => e.dst === selected) : [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {NODE_TYPES.map((t) => (
          <Stat key={t} label={`${t === "Person" ? "People" : `${t}s`}`} value={data.nodes.filter((n) => nodeType(n) === t).length} />
        ))}
        <Stat label="Relationships" value={data.edges.length} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card
          title="Nodes"
          actions={
            <div role="tablist" aria-label="Node type" className="flex flex-wrap gap-1">
              {NODE_TYPES.map((t) => (
                <Button key={t} size="sm" variant={type === t ? "primary" : "secondary"} role="tab" aria-selected={type === t} onClick={() => setType(t)}>
                  {t}
                </Button>
              ))}
            </div>
          }
        >
          <input
            aria-label="Filter nodes"
            className={cx(inputClass, "mb-3")}
            placeholder="Filter by name or ID"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {nodes.length === 0 ? (
            <p className="text-sm text-muted">No matching nodes.</p>
          ) : (
            <ul className="-mx-4 -mb-4 max-h-[32rem] divide-y divide-line overflow-y-auto border-t border-line">
              {nodes.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(n.id)}
                    aria-pressed={selected === n.id}
                    className={cx("flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm hover:bg-surface-2", selected === n.id && "bg-accent-soft")}
                  >
                    <span className="min-w-0">
                      <span className="block truncate">{label(n, n.id)}</span>
                      <span className="block truncate font-mono text-xs text-muted">{n.id}</span>
                    </span>
                    <span className="shrink-0 text-xs text-muted">{plural(degree.get(n.id) ?? 0, "link")}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={sel ? label(sel, sel.id) : "Relationships"} description={sel ? `${sel.labels.join(", ")}${sel.status ? `, ${sel.status}` : ""}` : "Choose a node to see what it is connected to."}>
          {!sel ? (
            <ul className="space-y-1 text-sm">
              {relCounts.map(([rel, n]) => (
                <li key={rel} className="flex justify-between gap-3">
                  <span className="font-mono text-xs">{rel}</span>
                  <span className="tabular-nums text-muted">{n}</span>
                </li>
              ))}
            </ul>
          ) : outgoing.length + incoming.length === 0 ? (
            <p className="text-sm text-muted">Not connected to anything.</p>
          ) : (
            <div className="space-y-4 text-sm">
              {[{ title: "Outgoing", edges: outgoing, other: (e: (typeof outgoing)[number]) => e.dst }, { title: "Incoming", edges: incoming, other: (e: (typeof incoming)[number]) => e.src }]
                .filter((g) => g.edges.length > 0)
                .map((g) => (
                  <div key={g.title}>
                    <h3 className="text-xs font-medium text-muted">{g.title}</h3>
                    <ul className="mt-1 space-y-1">
                      {g.edges.map((e, i) => {
                        const otherId = g.other(e);
                        return (
                          <li key={i} className="flex flex-wrap items-center gap-2">
                            <Badge>{e.rel}</Badge>
                            <button type="button" className="text-accent hover:underline" onClick={() => setSelected(otherId)}>
                              {label(byId.get(otherId), otherId)}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

export function GraphView() {
  const { data, error, loading, reload } = useAsync(api.graph, []);
  return (
    <>
      <PageHeader
        title="Graph data"
        description="Everything stored in the knowledge graph: people, knowledge items, documents, interview answers and how they connect."
        actions={<Button onClick={reload} disabled={loading}>Refresh</Button>}
      />
      {error ? (
        <ErrorAlert error={error} onRetry={reload} />
      ) : !data ? (
        <Loading />
      ) : data.nodes.length === 0 ? (
        <EmptyState title="The graph is empty">Import data to see it here.</EmptyState>
      ) : (
        <Explorer data={data} />
      )}
    </>
  );
}
