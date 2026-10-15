"use client";

import Link from "next/link";
import { useState } from "react";

import { useApp } from "@/components/app-context";
import { RequireLeaver } from "@/components/require-leaver";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  EmptyState,
  ErrorAlert,
  Loading,
  PageHeader,
  ProgressBar,
  Stat,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { Person } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

function ServiceStatus() {
  const { health, healthError, reloadHealth } = useApp();
  // A 503 from /health still says which store is down.
  const down =
    healthError instanceof ApiError && healthError.code === "SERVICE_UNAVAILABLE"
      ? (healthError.details as Record<string, string> | null)
      : null;
  const graph = health?.graph ?? down?.graph;
  const database = health?.database ?? down?.database;

  const row = (label: string, state: string | undefined, detail: string) => (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted">{detail}</p>
      </div>
      {state === "up" && <Badge tone="ok">Connected</Badge>}
      {state === "down" && <Badge tone="danger">Unreachable</Badge>}
      {state === undefined && <Badge>Unknown</Badge>}
    </li>
  );

  return (
    <Card title="Services" actions={<Button size="sm" onClick={reloadHealth}>Check again</Button>}>
      {healthError && !down ? (
        <ErrorAlert error={healthError} />
      ) : (
        <ul className="divide-y divide-line">
          {row("Knowledge graph", graph, "FalkorDB: people, items, documents and interview answers")}
          {row("Database", database, "Postgres: interview transcripts and saved handover plans")}
          <li className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div>
              <p className="text-sm font-medium">Language model</p>
              <p className="text-xs text-muted">
                {health?.llm === false
                  ? "Not configured. Questions and plan summaries use templates, and answers are saved without classification or follow-up questions."
                  : "Writes interview questions, analyses answers and summarises plans."}
              </p>
            </div>
            {health === undefined ? <Badge>Unknown</Badge> : health.llm ? <Badge tone="ok">Configured</Badge> : <Badge tone="warn">Not configured</Badge>}
          </li>
        </ul>
      )}
    </Card>
  );
}

function CoverageCard({ leaver }: { leaver: Person }) {
  const { data, error, loading, reload } = useAsync(() => api.coverage(leaver.id), [leaver.id]);
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return <Card title={`Coverage for ${leaver.name}`}>{loading && <Loading />}</Card>;

  const openGaps = data.items.filter((g) => g.open).slice(0, 5);
  return (
    <Card
      title={`Coverage for ${leaver.name}`}
      description="Items only this person knows about, and how many an interview answer now explains."
    >
      {data.unique_items === 0 ? (
        <p className="text-sm text-muted">
          {leaver.name} has no items that are undocumented or that only they worked on.
        </p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Unique items" value={data.unique_items} />
            <Stat label="Explained" value={data.covered} />
            <Stat label="Still open" value={data.open} />
            <Stat label="Risk-weighted" value={`${data.risk_weighted_percent}%`} note="weighted by what depends on each item" />
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>Explained</span>
              <span className="tabular-nums">{data.percent}%</span>
            </div>
            <ProgressBar value={data.percent} label="Share of unique items explained" />
          </div>
          {openGaps.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">Highest-risk open gaps</h3>
              <ul className="mt-2 divide-y divide-line rounded-md border border-line">
                {openGaps.map((g) => (
                  <li key={g.item_id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
                    <span className="min-w-0">{g.name}</span>
                    <span className="text-xs text-muted">risk {g.risk}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-sm">
                <Link className="text-accent hover:underline" href="/gaps">See all gaps</Link>
              </p>
            </div>
          )}
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
        <ButtonLink href="/interview" variant="primary">
          {data.open > 0 ? "Interview about open gaps" : "Open the interview"}
        </ButtonLink>
        <ButtonLink href="/handover">Build a handover plan</ButtonLink>
      </div>
    </Card>
  );
}

function GetStarted() {
  const { reloadPeople } = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function seed() {
    setBusy(true);
    setError(null);
    try {
      await api.seed();
      reloadPeople();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <EmptyState
      title="The knowledge graph is empty"
      action={
        <>
          <Button variant="primary" onClick={seed} busy={busy} busyLabel="Loading demo...">Load demo company</Button>
          <ButtonLink href="/import">Import your own data</ButtonLink>
        </>
      }
    >
      The demo company is fictional: Ravi, a senior engineer, is leaving, and three colleagues
      will take over his work.
      {error ? <div className="mt-3 text-left"><ErrorAlert error={error} /></div> : null}
    </EmptyState>
  );
}

export function OverviewView() {
  const { people, peopleLoaded, health } = useApp();
  return (
    <>
      <PageHeader
        title="Overview"
        description="Find what a departing employee knows that nobody else does, capture it in an interview, and hand it to the people taking over."
      />
      <div className="space-y-6">
        {peopleLoaded && people.length === 0 ? <GetStarted /> : <RequireLeaver>{(l) => <CoverageCard leaver={l} />}</RequireLeaver>}
        {health?.llm === false && (
          <Alert tone="warn" title="No language model configured">
            Brain-dump import and voice interviews need one. Set OPENROUTER_API_KEY on the API
            server and restart it to turn them on.
          </Alert>
        )}
        <ServiceStatus />
      </div>
    </>
  );
}
