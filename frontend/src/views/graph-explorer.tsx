"use client";

import { useMemo, useState, type FormEvent } from "react";

import { GraphCanvas, type GraphSelection } from "@/components/graph-canvas";
import { Alert, Button, ButtonLink, Card, cx, EmptyState, ErrorAlert, inputClass, Loading, PageHeader, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { plural } from "@/lib/format";
import { caption, formatProperty, labelColor, nodeMatches, primaryLabel } from "@/lib/graph-style";
import type { RawEdge, RawNode } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { GraphTable } from "@/views/graph";

const LIMITS = [250, 500, 1000, 2000, 5000];

function Swatch({ color }: { color: string }) {
  return <span aria-hidden className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: color }} />;
}

function Toggle({ on, onClick, children, title }: { on: boolean; onClick: () => void; children: React.ReactNode; title: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      title={title}
      onClick={onClick}
      className={cx(
        "inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs",
        on ? "border-line bg-surface text-fg" : "border-dashed border-line bg-transparent text-muted line-through",
      )}
    >
      {children}
    </button>
  );
}

function Properties({ properties }: { properties: Record<string, RawNode["properties"][string]> }) {
  const entries = Object.entries(properties).sort(([a], [b]) => a.localeCompare(b));
  if (entries.length === 0) return <p className="text-sm text-muted">No properties.</p>;
  return (
    <dl className="divide-y divide-line rounded-md border border-line text-sm">
      {entries.map(([key, value]) => (
        <div key={key} className="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] gap-2 px-3 py-1.5">
          <dt className="truncate font-mono text-xs text-muted" title={key}>{key}</dt>
          <dd className="whitespace-pre-wrap break-words">{formatProperty(key, value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function NodeLink({ node, onPick }: { node: RawNode | undefined; onPick: (id: number) => void }) {
  if (!node) return <span className="text-muted">a node outside this view</span>;
  return (
    <button type="button" className="inline-flex items-center gap-1.5 text-left text-accent hover:underline" onClick={() => onPick(node.id)}>
      <Swatch color={labelColor(primaryLabel(node.labels))} />
      {caption(node)}
    </button>
  );
}

function NodeDetails({
  node,
  edges,
  byId,
  onPick,
  onExpand,
}: {
  node: RawNode;
  edges: RawEdge[];
  byId: Map<number, RawNode>;
  onPick: (sel: GraphSelection) => void;
  onExpand: (id: number) => Promise<number>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [added, setAdded] = useState<number | null>(null);
  const touching = edges.filter((e) => e.source === node.id || e.target === node.id);

  async function expand() {
    setBusy(true);
    setError(null);
    setAdded(null);
    try {
      setAdded(await onExpand(node.id));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <h2 className="font-semibold break-words">{caption(node)}</h2>
        <div className="flex flex-wrap gap-1.5">
          {node.labels.map((l) => (
            <span key={l} className="inline-flex items-center gap-1.5 rounded border border-line px-1.5 py-0.5 text-xs">
              <Swatch color={labelColor(l)} />
              {l}
            </span>
          ))}
        </div>
        <p className="text-xs text-muted">Internal id {node.id}</p>
      </div>
      <div className="space-y-1.5">
        <h3 className="text-xs font-medium text-muted">Properties</h3>
        <Properties properties={node.properties} />
      </div>
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-medium text-muted">{plural(touching.length, "relationship")} in view</h3>
          <Button size="sm" onClick={expand} busy={busy} busyLabel="Loading...">Load all neighbours</Button>
        </div>
        {added !== null && (
          <p className="text-xs text-muted" role="status">
            {added === 0 ? "Every neighbour was already shown." : `Added ${plural(added, "node")}.`}
          </p>
        )}
        <ErrorAlert error={error} />
        {touching.length > 0 && (
          <ul className="space-y-1 text-sm">
            {touching.map((e) => {
              const out = e.source === node.id;
              return (
                <li key={e.id} className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <button type="button" className="font-mono text-xs text-muted hover:text-fg hover:underline" onClick={() => onPick({ kind: "edge", id: e.id })}>
                    {out ? `${e.type} to` : `${e.type} from`}
                  </button>
                  <NodeLink node={byId.get(out ? e.target : e.source)} onPick={(id) => onPick({ kind: "node", id })} />
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function EdgeDetails({ edge, byId, onPick }: { edge: RawEdge; byId: Map<number, RawNode>; onPick: (sel: GraphSelection) => void }) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <h2 className="font-mono font-semibold">{edge.type}</h2>
        <p className="flex flex-wrap items-center gap-x-2 text-sm">
          <span className="text-muted">From</span>
          <NodeLink node={byId.get(edge.source)} onPick={(id) => onPick({ kind: "node", id })} />
        </p>
        <p className="flex flex-wrap items-center gap-x-2 text-sm">
          <span className="text-muted">To</span>
          <NodeLink node={byId.get(edge.target)} onPick={(id) => onPick({ kind: "node", id })} />
        </p>
        <p className="text-xs text-muted">Internal id {edge.id}</p>
      </div>
      <div className="space-y-1.5">
        <h3 className="text-xs font-medium text-muted">Properties</h3>
        <Properties properties={edge.properties} />
      </div>
    </div>
  );
}

function toggled(set: ReadonlySet<string>, key: string): Set<string> {
  const next = new Set(set);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}

function Explorer() {
  const [limit, setLimit] = useState(1000);
  const snapshot = useAsync(() => api.graphSnapshot([], limit), [limit]);
  const schema = useAsync(api.graphSchema, [limit]);
  // Nodes and edges added with "Load all neighbours", on top of the snapshot.
  const [extra, setExtra] = useState<{ nodes: RawNode[]; edges: RawEdge[] }>({ nodes: [], edges: [] });
  const [hiddenLabels, setHiddenLabels] = useState<ReadonlySet<string>>(new Set());
  const [hiddenTypes, setHiddenTypes] = useState<ReadonlySet<string>>(new Set());
  const [selection, setSelection] = useState<GraphSelection | null>(null);
  const [query, setQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const [focus, setFocus] = useState<{ id: number; nonce: number } | null>(null);
  const [fitNonce, setFitNonce] = useState(0);

  const { nodes, edges, byId } = useMemo(() => {
    const byId = new Map<number, RawNode>();
    for (const n of [...(snapshot.data?.nodes ?? []), ...extra.nodes]) if (!byId.has(n.id)) byId.set(n.id, n);
    const edgeById = new Map<number, RawEdge>();
    for (const e of [...(snapshot.data?.edges ?? []), ...extra.edges]) if (!edgeById.has(e.id)) edgeById.set(e.id, e);
    return { nodes: [...byId.values()], edges: [...edgeById.values()], byId };
  }, [snapshot.data, extra]);

  const labelCounts = useMemo(() => {
    const c = new Map<string, number>();
    for (const n of nodes) for (const l of n.labels) c.set(l, (c.get(l) ?? 0) + 1);
    return [...c.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [nodes]);
  const typeCounts = useMemo(() => {
    const c = new Map<string, number>();
    for (const e of edges) c.set(e.type, (c.get(e.type) ?? 0) + 1);
    return [...c.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [edges]);

  const matchList = useMemo(() => (query.trim() ? nodes.filter((n) => nodeMatches(n, query)).map((n) => n.id) : []), [nodes, query]);
  const matches = useMemo(() => new Set(matchList), [matchList]);

  function pick(sel: GraphSelection | null) {
    setSelection(sel);
    if (sel?.kind === "node") setFocus((f) => ({ id: sel.id, nonce: (f?.nonce ?? 0) + 1 }));
  }

  function reload() {
    setExtra({ nodes: [], edges: [] });
    setSelection(null);
    snapshot.reload();
    schema.reload();
  }

  function findNext(e: FormEvent) {
    e.preventDefault();
    if (matchList.length === 0) return;
    const i = matchIndex % matchList.length;
    setMatchIndex(i + 1);
    pick({ kind: "node", id: matchList[i] });
  }

  async function expand(id: number): Promise<number> {
    const found = await api.graphNeighbors(id);
    setExtra((x) => ({ nodes: [...x.nodes, ...found.nodes], edges: [...x.edges, ...found.edges] }));
    return found.nodes.filter((n) => !byId.has(n.id)).length; // nodes that were not on screen yet
  }

  const selectedNode = selection?.kind === "node" ? byId.get(selection.id) : undefined;
  const selectedEdge = selection?.kind === "edge" ? edges.find((e) => e.id === selection.id) : undefined;

  if (snapshot.error && !snapshot.data) return <ErrorAlert error={snapshot.error} onRetry={reload} />;
  if (!snapshot.data) return <Loading label="Loading the graph..." />;
  if (snapshot.data.nodes.length === 0) {
    return (
      <EmptyState title="The graph is empty" action={<ButtonLink href="/import" variant="primary">Import data</ButtonLink>}>
        Load the demo company or import your own sources to see the graph here.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      {schema.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Nodes in FalkorDB" value={schema.data.node_count} />
          <Stat label="Relationships in FalkorDB" value={schema.data.edge_count} />
          <Stat label="Nodes shown" value={nodes.length} />
          <Stat label="Relationships shown" value={edges.length} />
        </div>
      )}

      {snapshot.data.truncated && (
        <Alert tone="warn" title={`Showing the first ${limit} nodes`}>
          The graph has more. Raise the node limit, or select a node and load all its neighbours.
        </Alert>
      )}

      <Card>
        <div className="space-y-3">
          <div className="flex flex-wrap items-end gap-2">
            <form onSubmit={findNext} className="flex min-w-60 flex-1 gap-2" role="search">
              <input
                aria-label="Search nodes"
                className={inputClass}
                placeholder="Search names, ids and property values"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setMatchIndex(0);
                }}
              />
              <Button type="submit" disabled={matchList.length === 0}>Find</Button>
            </form>
            <label className="flex items-center gap-2 text-sm">
              <span className="text-muted">Node limit</span>
              <select
                className={cx(inputClass, "w-auto py-1.5")}
                value={limit}
                onChange={(e) => {
                  setExtra({ nodes: [], edges: [] });
                  setSelection(null);
                  setLimit(Number(e.target.value));
                }}
              >
                {LIMITS.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </label>
            <Button onClick={() => setFitNonce((n) => n + 1)}>Fit to view</Button>
            <Button onClick={reload} disabled={snapshot.loading}>Reload</Button>
          </div>
          {query.trim() && (
            <p className="text-xs text-muted" role="status">
              {matchList.length === 0 ? "No matching nodes." : `${plural(matchList.length, "match", "matches")}. Press Find to step through them.`}
            </p>
          )}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-xs text-muted">Labels</span>
              {labelCounts.map(([l, n]) => (
                <Toggle key={l} on={!hiddenLabels.has(l)} onClick={() => setHiddenLabels((s) => toggled(s, l))} title={`Show or hide nodes labelled ${l}`}>
                  <Swatch color={labelColor(l)} />
                  {l} <span className="tabular-nums text-muted">{n}</span>
                </Toggle>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-xs text-muted">Relationships</span>
              {typeCounts.map(([t, n]) => (
                <Toggle key={t} on={!hiddenTypes.has(t)} onClick={() => setHiddenTypes((s) => toggled(s, t))} title={`Show or hide ${t} relationships`}>
                  <span className="font-mono">{t}</span> <span className="tabular-nums text-muted">{n}</span>
                </Toggle>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="overflow-hidden rounded-lg border border-line bg-surface">
          <GraphCanvas
            className="h-[70vh] min-h-[420px] w-full"
            nodes={nodes}
            edges={edges}
            hiddenLabels={hiddenLabels}
            hiddenTypes={hiddenTypes}
            matches={matches}
            selection={selection}
            onSelect={pick}
            focus={focus}
            fitNonce={fitNonce}
          />
          <p className="border-t border-line px-3 py-2 text-xs text-muted">
            Drag nodes to move them, scroll to zoom, drag the background to pan. On large graphs,
            names appear as you zoom in. The Table tab lists the same data as text.
          </p>
        </div>
        <Card className="min-w-0 self-start">
          {selectedNode ? (
            <NodeDetails key={selectedNode.id} node={selectedNode} edges={edges} byId={byId} onPick={pick} onExpand={expand} />
          ) : selectedEdge ? (
            <EdgeDetails edge={selectedEdge} byId={byId} onPick={pick} />
          ) : (
            <p className="text-sm text-muted">
              Select a node or relationship to see all of its properties, exactly as stored in FalkorDB.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

export function GraphView() {
  const [tab, setTab] = useState<"visual" | "table">("visual");
  const tabButton = (value: typeof tab, label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={tab === value}
      onClick={() => setTab(value)}
      className={cx(
        "border-b-2 px-3 py-2 text-sm",
        tab === value ? "border-accent font-medium text-accent" : "border-transparent text-muted hover:text-fg",
      )}
    >
      {label}
    </button>
  );

  return (
    <>
      <PageHeader
        title="Graph"
        description="The knowledge graph as stored in FalkorDB: every node, relationship and property."
      />
      <div role="tablist" aria-label="Graph view" className="mb-4 flex border-b border-line">
        {tabButton("visual", "Visual")}
        {tabButton("table", "Table")}
      </div>
      {tab === "visual" ? <Explorer /> : <GraphTable />}
    </>
  );
}
