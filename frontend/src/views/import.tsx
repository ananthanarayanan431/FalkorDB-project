"use client";

import { useState, type ChangeEvent } from "react";

import { useApp } from "@/components/app-context";
import { Alert, Button, Card, ErrorAlert, Field, inputClass, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { plural } from "@/lib/format";
import type { BrainDumpResult, IngestCounts } from "@/lib/types";

const EXAMPLE_BUNDLE = {
  people: [
    { id: "alex", name: "Alex Kim", role: "Data Engineer", seniority: "senior", status: "leaving" },
    { id: "jo", name: "Jo Patel", role: "Data Engineer", seniority: "junior" },
  ],
  items: [
    { id: "nightly-export", name: "Nightly export", kind: "system", description: "Exports orders to the warehouse." },
    { id: "export-batch-size", name: "Why the export uses batches of 500", kind: "decision" },
  ],
  documents: [{ id: "export-runbook", title: "Export runbook", covers: ["nightly-export"] }],
  contributions: [
    { person: "alex", item: "nightly-export", rel: "OWNS", source: "code", ref: "repo/export" },
    { person: "alex", item: "export-batch-size", rel: "AUTHORED", source: "code" },
  ],
  links: [{ src: "export-batch-size", rel: "DEPENDS_ON", dst: "nightly-export" }],
  knows: [{ person: "jo", item: "nightly-export", level: 1 }],
};

function CountsSummary({ counts }: { counts: IngestCounts }) {
  const parts = [
    plural(counts.people, "person", "people"),
    plural(counts.items, "item"),
    plural(counts.documents, "document"),
    plural(counts.contributions, "contribution"),
    plural(counts.links, "link"),
    plural(counts.knows, "knowledge level"),
  ];
  return <>Written: {parts.join(", ")}.</>;
}

function DemoCard() {
  const { reloadPeople } = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<IngestCounts | null>(null);

  async function seed() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.seed());
      reloadPeople();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="Demo company"
      description="A fictional payments team. Ravi Menon (senior) is leaving; Priya Nair (mid-level), Sam Carter (junior) and Meera Iyer (senior) stay."
    >
      <div className="space-y-3">
        <p className="text-sm text-muted">
          Loading it again is safe: records are merged by id, so nothing is duplicated.
        </p>
        <Button variant="primary" onClick={seed} busy={busy} busyLabel="Loading...">Load demo company</Button>
        {result && <Alert tone="ok"><CountsSummary counts={result} /></Alert>}
        <ErrorAlert error={error} />
      </div>
    </Card>
  );
}

function BundleCard() {
  const { reloadPeople } = useApp();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<IngestCounts | null>(null);

  async function loadFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setText(await file.text());
    setResult(null);
    setError(null);
  }

  async function submit() {
    setError(null);
    setResult(null);
    let bundle: unknown;
    try {
      bundle = JSON.parse(text);
    } catch (e) {
      setError(new Error(`This is not valid JSON: ${e instanceof Error ? e.message : String(e)}`));
      return;
    }
    setBusy(true);
    try {
      setResult(await api.ingestSources(bundle));
      reloadPeople();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="Source bundle"
      description="Structured data from your own systems: people, items, documents, who worked on what, how items relate, and what each person already knows."
    >
      <div className="space-y-3">
        <Field
          label="Bundle JSON"
          htmlFor="bundle"
          hint="If the bundle refers to a person or item that exists neither in it nor in the graph, nothing is written and each bad reference is listed."
        >
          <textarea
            id="bundle"
            className={`${inputClass} min-h-64 font-mono text-xs`}
            spellCheck={false}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder='{"people": [], "items": [], "documents": [], "contributions": [], "links": [], "knows": []}'
          />
        </Field>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="primary" onClick={submit} busy={busy} busyLabel="Importing..." disabled={!text.trim()}>
            Import bundle
          </Button>
          <label className="cursor-pointer rounded-md border border-line bg-surface px-3.5 py-2 text-sm font-medium hover:bg-surface-2">
            Choose a JSON file
            <input type="file" accept="application/json,.json" className="sr-only" onChange={loadFile} />
          </label>
          <Button variant="ghost" onClick={() => setText(JSON.stringify(EXAMPLE_BUNDLE, null, 2))}>
            Insert example
          </Button>
        </div>
        {result && <Alert tone="ok"><CountsSummary counts={result} /></Alert>}
        <ErrorAlert error={error} />
      </div>
    </Card>
  );
}

function BrainDumpCard() {
  const { people, health, leaver } = useApp();
  const [person, setPerson] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<BrainDumpResult | null>(null);
  const who = person || leaver?.id || "";
  const noLlm = health?.llm === false;

  async function submit() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.brainDump(who, text));
      setText("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="Brain dump"
      description="The leaver describes their work in their own words. The language model turns it into items, dependencies and prerequisites in the graph."
    >
      {people.length === 0 ? (
        <p className="text-sm text-muted">Add the person first, through the demo, a source bundle or the People page.</p>
      ) : (
        <div className="space-y-3">
          {noLlm && (
            <Alert tone="warn">
              This needs a language model. Set OPENROUTER_API_KEY on the API server to use it.
            </Alert>
          )}
          <Field label="Whose notes are these" htmlFor="bd-person">
            <select id="bd-person" className={inputClass} value={who} onChange={(e) => setPerson(e.target.value)}>
              {!who && <option value="">Choose a person</option>}
              {people.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Notes" htmlFor="bd-text" hint="Only what they actually say is extracted; nothing is invented.">
            <textarea
              id="bd-text"
              className={`${inputClass} min-h-40`}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="For example: I own the export job. It depends on the orders API, and anyone touching it should understand the warehouse schema first."
            />
          </Field>
          <Button
            variant="primary"
            onClick={submit}
            busy={busy}
            busyLabel="Extracting..."
            disabled={noLlm || !who || !text.trim()}
          >
            Extract into the graph
          </Button>
          {result && (
            <Alert tone="ok" title={`Found ${plural(result.items_found, "item")}.`}>
              {result.new_items.length > 0
                ? `New in the graph: ${result.new_items.join(", ")}.`
                : "All of them were already in the graph."}
            </Alert>
          )}
          <ErrorAlert error={error} />
        </div>
      )}
    </Card>
  );
}

export function ImportView() {
  return (
    <>
      <PageHeader
        title="Import data"
        description="Fill the knowledge graph from structured sources, from the leaver's own notes, or both. Records with the same id are merged."
      />
      <div className="space-y-6">
        <DemoCard />
        <BundleCard />
        <BrainDumpCard />
      </div>
    </>
  );
}
