"use client";

import { useState } from "react";

import { useApp } from "@/components/app-context";
import { RequireLeaver } from "@/components/require-leaver";
import {
  Alert,
  Badge,
  Button,
  Card,
  cx,
  EmptyState,
  ErrorAlert,
  Field,
  inputClass,
  Loading,
  PageHeader,
} from "@/components/ui";
import { api } from "@/lib/api";
import {
  ANSWER_TYPE_LABEL,
  formatDateTime,
  plural,
  SENIORITY_LABEL,
  SOURCE_LABEL,
  STRATEGY_LABEL,
} from "@/lib/format";
import type { Person, Plan, PlanStep } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

function Step({ step }: { step: PlanStep }) {
  return (
    <li className="flex gap-3 px-4 py-4">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded border border-line text-xs font-medium tabular-nums">
        {step.order}
      </span>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="font-medium">{step.name}</h4>
          <Badge tone={step.mode === "learn" ? "accent" : "neutral"}>{step.mode === "learn" ? "Learn" : "Read"}</Badge>
          <span className="text-xs capitalize text-muted">{step.kind}</span>
          {step.risk > 0 && <span className="text-xs text-muted">risk {step.risk}</span>}
        </div>
        <p className="text-xs text-muted">{step.why_included}</p>
        {step.description && <p className="text-sm">{step.description}</p>}
        {step.learn_first.length > 0 && (
          <p className="text-sm"><span className="text-muted">Learn first:</span> {step.learn_first.join(", ")}</p>
        )}
        {step.read.length > 0 && (
          <p className="text-sm"><span className="text-muted">Read:</span> {step.read.join(", ")}</p>
        )}
        {step.knowledge.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted">From the leaver</p>
            <ul className="space-y-2">
              {step.knowledge.map((k, i) => (
                <li key={i} className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm">
                  <p className="whitespace-pre-wrap">{k.text}</p>
                  <p className="mt-1 text-xs text-muted">
                    {ANSWER_TYPE_LABEL[k.kind] ?? k.kind}, {SOURCE_LABEL[k.source] ?? k.source}, {formatDateTime(k.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </li>
  );
}

export function PlanView({ plan, note }: { plan: Plan; note?: string }) {
  const r = plan.receiver;
  return (
    <Card
      title={`Plan for ${r.name}`}
      description={`${r.role ? `${r.role}, ` : ""}${SENIORITY_LABEL[r.seniority]}. Strategy: ${STRATEGY_LABEL[plan.strategy]}.${note ? ` ${note}` : ""}`}
    >
      <div className="space-y-3">
        <p className="text-sm leading-relaxed">{plan.summary}</p>
        {plan.skipped_already_known > 0 && (
          <p className="text-xs text-muted">
            {plural(plan.skipped_already_known, "item")} left out because {r.name} already knows {plan.skipped_already_known === 1 ? "it" : "them"}.
          </p>
        )}
      </div>
      {plan.steps.length === 0 ? (
        <p className="mt-4 text-sm text-muted">Nothing to hand over: {r.name} already knows everything the leaver worked on.</p>
      ) : (
        <ol className="-mx-4 -mb-4 mt-4 divide-y divide-line border-t border-line">
          {plan.steps.map((s) => <Step key={s.item_id} step={s} />)}
        </ol>
      )}
    </Card>
  );
}

function SavedPlans({ leaver, version, onOpen, openId }: { leaver: Person; version: number; onOpen: (id: string) => void; openId: string | null }) {
  const { people } = useApp();
  const { data, error, loading, reload } = useAsync(() => api.plans({ leaver: leaver.id }), [leaver.id, version]);
  const name = (id: string) => people.find((p) => p.id === id)?.name ?? id;

  return (
    <Card title="Saved plans" description="Each saved plan is kept exactly as it was given, even after the graph changes.">
      {error ? (
        <ErrorAlert error={error} onRetry={reload} />
      ) : !data ? (
        loading && <Loading />
      ) : data.length === 0 ? (
        <p className="text-sm text-muted">No saved plans for {leaver.name} yet.</p>
      ) : (
        <ul className="-m-4 divide-y divide-line">
          {data.map((p) => (
            <li key={p.id} className={cx("flex flex-wrap items-center justify-between gap-3 px-4 py-3", openId === p.id && "bg-accent-soft")}>
              <div className="min-w-0">
                <p className="text-sm font-medium">{name(p.receiver)}</p>
                <p className="text-xs text-muted">
                  {plural(p.step_count, "step")}, {STRATEGY_LABEL[p.strategy]}, saved {formatDateTime(p.created_at)}
                </p>
              </div>
              <Button size="sm" onClick={() => onOpen(p.id)} disabled={openId === p.id}>
                {openId === p.id ? "Showing" : "Open"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SavedPlanView({ id }: { id: string }) {
  const { data, error, loading, reload } = useAsync(() => api.plan(id), [id]);
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return loading ? <Loading /> : null;
  return <PlanView plan={data.plan} note={`Saved ${formatDateTime(data.created_at)}.`} />;
}

function Handover({ leaver }: { leaver: Person }) {
  const { people } = useApp();
  const receivers = people.filter((p) => p.id !== leaver.id);
  const [picked, setPicked] = useState("");
  const receiver = receivers.some((p) => p.id === picked) ? picked : (receivers[0]?.id ?? "");
  const [busy, setBusy] = useState<"preview" | "save" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [shown, setShown] = useState<{ kind: "preview"; plan: Plan } | { kind: "saved"; id: string } | null>(null);
  const [version, setVersion] = useState(0);
  const [savedNote, setSavedNote] = useState<string | null>(null);

  async function run(kind: "preview" | "save") {
    setBusy(kind);
    setError(null);
    setSavedNote(null);
    try {
      if (kind === "preview") {
        setShown({ kind, plan: await api.previewPlan(receiver, leaver.id) });
      } else {
        const saved = await api.savePlan(receiver, leaver.id);
        setShown({ kind: "saved", id: saved.id });
        setVersion((v) => v + 1);
        setSavedNote(`Plan for ${saved.plan.receiver.name} saved.`);
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  }

  if (receivers.length === 0) {
    return (
      <EmptyState title="Nobody to hand over to">
        Add the people taking over {leaver.name}&apos;s work on the People page or through an import.
      </EmptyState>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0 space-y-6">
        <Card
          title={`Hand over ${leaver.name}'s knowledge`}
          description="Each receiver gets what the leaver knew minus what they already know, ordered so prerequisites come first. Juniors get every missing foundation; mid-level and senior people get only what is not written down."
        >
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-56 flex-1">
              <Field label="Receiver" htmlFor="receiver">
                <select id="receiver" className={inputClass} value={receiver} onChange={(e) => setPicked(e.target.value)}>
                  {receivers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({SENIORITY_LABEL[p.seniority]}{p.role ? `, ${p.role}` : ""})
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <Button onClick={() => run("preview")} busy={busy === "preview"} busyLabel="Building..." disabled={busy !== null}>
              Preview
            </Button>
            <Button variant="primary" onClick={() => run("save")} busy={busy === "save"} busyLabel="Saving..." disabled={busy !== null}>
              Build and save
            </Button>
          </div>
          <div className="mt-3 space-y-2">
            {savedNote && <Alert tone="ok">{savedNote}</Alert>}
            <ErrorAlert error={error} />
          </div>
        </Card>
        {shown?.kind === "preview" && <PlanView plan={shown.plan} note="Preview, not saved." />}
        {shown?.kind === "saved" && <SavedPlanView key={shown.id} id={shown.id} />}
      </div>
      <div className="min-w-0">
        <SavedPlans
          leaver={leaver}
          version={version}
          openId={shown?.kind === "saved" ? shown.id : null}
          onOpen={(id) => {
            setSavedNote(null);
            setShown({ kind: "saved", id });
          }}
        />
      </div>
    </div>
  );
}

export function HandoverView() {
  return (
    <>
      <PageHeader
        title="Handover plans"
        description="A different plan for each person taking over, built from the knowledge graph and the interview answers."
      />
      <RequireLeaver>{(leaver) => <Handover leaver={leaver} />}</RequireLeaver>
    </>
  );
}
