"use client";

import { useState } from "react";

import { RequireLeaver } from "@/components/require-leaver";
import { Badge, ButtonLink, Card, EmptyState, ErrorAlert, Loading, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { plural } from "@/lib/format";
import type { Gap, Person } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

function GapRow({ gap }: { gap: Gap }) {
  return (
    <tr className="align-top">
      <td className="px-3 py-3">
        <p className="font-medium">{gap.name}</p>
        {gap.description && <p className="mt-0.5 text-xs text-muted">{gap.description}</p>}
        <p className="mt-0.5 font-mono text-xs text-muted">{gap.item_id}</p>
      </td>
      <td className="px-3 py-3 capitalize">{gap.kind}</td>
      <td className="px-3 py-3 tabular-nums">{gap.risk}</td>
      <td className="px-3 py-3">
        <ul className="space-y-0.5 text-sm">
          {gap.reasons.map((r) => <li key={r}>{r}</li>)}
        </ul>
      </td>
      <td className="px-3 py-3 tabular-nums">{gap.answers}</td>
      <td className="px-3 py-3">{gap.open ? <Badge tone="warn">Open</Badge> : <Badge tone="ok">Explained</Badge>}</td>
    </tr>
  );
}

function GapsTable({ leaver }: { leaver: Person }) {
  const [showAll, setShowAll] = useState(false);
  const { data, error, loading, reload } = useAsync(() => api.gaps(leaver.id, !showAll), [leaver.id, showAll]);

  return (
    <Card
      title={data ? `${plural(data.length, showAll ? "unique item" : "open gap")} for ${leaver.name}` : `Gaps for ${leaver.name}`}
      description="Risk is the number of items that depend on it, plus 2 if only the leaver worked on it and 2 if it has no documentation."
      actions={
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Include explained items
        </label>
      }
    >
      {error ? (
        <ErrorAlert error={error} onRetry={reload} />
      ) : !data ? (
        loading && <Loading />
      ) : data.length === 0 ? (
        <EmptyState
          title={showAll ? "Nothing unique to this person" : "No open gaps"}
          action={!showAll && <ButtonLink href="/handover" variant="primary">Build a handover plan</ButtonLink>}
        >
          {showAll
            ? `Everything ${leaver.name} worked on is documented and shared with someone else.`
            : `Every item only ${leaver.name} knows about has an interview answer.`}
        </EmptyState>
      ) : (
        <>
          <div className="-mx-4 overflow-x-auto">
            <table className="w-full min-w-[44rem] text-left text-sm">
              <thead className="border-b border-line text-xs text-muted">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">Item</th>
                  <th scope="col" className="px-3 py-2 font-medium">Kind</th>
                  <th scope="col" className="px-3 py-2 font-medium">Risk</th>
                  <th scope="col" className="px-3 py-2 font-medium">Why it is a gap</th>
                  <th scope="col" className="px-3 py-2 font-medium">Answers</th>
                  <th scope="col" className="px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.map((g) => <GapRow key={g.item_id} gap={g} />)}
              </tbody>
            </table>
          </div>
          {data.some((g) => g.open) && (
            <div className="mt-4 border-t border-line pt-4">
              <ButtonLink href="/interview" variant="primary">Interview {leaver.name} about these</ButtonLink>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

export function GapsView() {
  return (
    <>
      <PageHeader
        title="Knowledge gaps"
        description="Items the leaver worked on that nobody else did, or that have no documentation. A gap stays open until an interview answer explains it."
      />
      <RequireLeaver>{(leaver) => <GapsTable leaver={leaver} />}</RequireLeaver>
    </>
  );
}
