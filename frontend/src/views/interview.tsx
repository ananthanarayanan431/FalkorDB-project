"use client";

import { useState } from "react";

import { RequireLeaver } from "@/components/require-leaver";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  cx,
  EmptyState,
  ErrorAlert,
  Field,
  inputClass,
  Loading,
  PageHeader,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { ANSWER_TYPE_LABEL, formatDateTime } from "@/lib/format";
import { useLocal } from "@/lib/local-store";
import type { AnswerResult, Interview, Person, Question, Turn } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { VoicePanel } from "@/views/voice-panel";

function QuestionBlock({ q }: { q: Question }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">{q.item_name}</span>
        <Badge>risk {q.risk}</Badge>
        {q.is_follow_up && <Badge tone="accent">Follow-up</Badge>}
      </div>
      <p className="text-base leading-relaxed">{q.text}</p>
      {q.reasons.length > 0 && (
        <p className="text-xs text-muted">Asked because: {q.reasons.join("; ")}.</p>
      )}
    </div>
  );
}

function TypedAnswer({ interview, onChange }: { interview: Interview; onChange: () => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<"answer" | "skip" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [last, setLast] = useState<AnswerResult | null>(null);
  const q = interview.question;

  async function run(kind: "answer" | "skip") {
    setBusy(kind);
    setError(null);
    setLast(null);
    try {
      if (kind === "answer") {
        setLast(await api.answer(interview.interview_id, text));
        setText("");
      } else {
        await api.skip(interview.interview_id);
      }
      onChange();
    } catch (e) {
      setError(e);
      // Someone else moved the interview on: show its current question.
      if (e instanceof ApiError && e.status === 409) onChange();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {last && (
        <Alert tone="ok" title="Answer saved">
          Stored as {ANSWER_TYPE_LABEL[last.answer_type] ?? last.answer_type}
          {last.new_items.length > 0 && `. New items found in it: ${last.new_items.join(", ")}`}.
        </Alert>
      )}
      <ErrorAlert error={error} />
      {q ? (
        <>
          <QuestionBlock q={q} />
          <Field label="Your answer" htmlFor="answer">
            <textarea
              id="answer"
              className={cx(inputClass, "min-h-36")}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Why it is built this way, what breaks if it changes, who to ask..."
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              onClick={() => run("answer")}
              busy={busy === "answer"}
              busyLabel="Saving..."
              disabled={busy !== null || !text.trim()}
            >
              Save answer
            </Button>
            <Button onClick={() => run("skip")} busy={busy === "skip"} busyLabel="Skipping..." disabled={busy !== null}>
              Skip question
            </Button>
          </div>
        </>
      ) : (
        <EmptyState
          title="No questions left"
          action={<ButtonLink href="/handover" variant="primary">Build handover plans</ButtonLink>}
        >
          Every open gap has been answered or skipped in this interview.
        </EmptyState>
      )}
    </div>
  );
}

function TurnItem({ turn }: { turn: Turn }) {
  return (
    <li className="space-y-1.5 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <span className="tabular-nums">#{turn.seq}</span>
        <span className="font-mono">{turn.item_id}</span>
        {turn.action === "skip" && <Badge tone="warn">Skipped</Badge>}
        {turn.action === "amend" && <Badge tone="accent">Addition</Badge>}
        {turn.is_follow_up && <Badge tone="accent">Follow-up</Badge>}
        {turn.answer_type && <Badge>{ANSWER_TYPE_LABEL[turn.answer_type] ?? turn.answer_type}</Badge>}
        <span>{formatDateTime(turn.created_at)}</span>
      </div>
      <p className="text-sm font-medium">{turn.question}</p>
      {turn.answer && <p className="whitespace-pre-wrap text-sm">{turn.answer}</p>}
      {turn.new_items.length > 0 && (
        <p className="text-xs text-muted">New items: {turn.new_items.join(", ")}</p>
      )}
    </li>
  );
}

function StartInterview({ leaver, onStarted }: { leaver: Person; onStarted: (id: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [resumeId, setResumeId] = useState("");

  async function start() {
    setBusy(true);
    setError(null);
    try {
      onStarted((await api.startInterview(leaver.id)).interview_id);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title={`Interview ${leaver.name}`}
      description="Questions are picked from the highest-risk open gaps. Answers are stored in the graph against the item they explain, and anything new they mention becomes its own item."
    >
      <div className="space-y-4">
        <Button variant="primary" onClick={start} busy={busy} busyLabel="Starting...">Start a new interview</Button>
        <ErrorAlert error={error} />
        <form
          className="flex flex-wrap items-end gap-2 border-t border-line pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (resumeId.trim()) onStarted(resumeId.trim());
          }}
        >
          <div className="min-w-48 flex-1">
            <Field label="Or continue an earlier interview" htmlFor="resume-id">
              <input
                id="resume-id"
                className={cx(inputClass, "font-mono")}
                value={resumeId}
                onChange={(e) => setResumeId(e.target.value)}
                placeholder="Interview ID"
              />
            </Field>
          </div>
          <Button type="submit" disabled={!resumeId.trim()}>Open</Button>
        </form>
      </div>
    </Card>
  );
}

function InterviewSession({ leaver, id, onClose }: { leaver: Person; id: string; onClose: () => void }) {
  const [mode, setMode] = useState<"type" | "voice">("type");
  const { data, error, loading, reload } = useAsync(() => api.interview(id), [id]);

  if (error && !data) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <Alert
        tone="danger"
        title={missing ? `Interview ${id} no longer exists` : "Could not load the interview"}
        action={<Button size="sm" onClick={onClose}>Start another</Button>}
      >
        {missing ? "It may have been removed by a data reset." : error instanceof Error ? error.message : String(error)}
      </Alert>
    );
  }
  if (!data) return loading ? <Loading /> : null;

  if (data.leaver !== leaver.id) {
    return (
      <Alert tone="warn" title={`Interview ${id} belongs to another person (${data.leaver})`} action={<Button size="sm" onClick={onClose}>Start another</Button>}>
        Switch the leaver in the header to continue it.
      </Alert>
    );
  }

  const tab = (value: "type" | "voice", label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={mode === value}
      onClick={() => setMode(value)}
      className={cx(
        "border-b-2 px-3 py-2 text-sm",
        mode === value ? "border-accent font-medium text-accent" : "border-transparent text-muted hover:text-fg",
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <Card
        title={`Interview with ${leaver.name}`}
        description={
          <>
            ID <span className="font-mono">{data.interview_id}</span>, {data.turns} answered
            {data.status === "completed" ? ", finished" : ""}
          </>
        }
        actions={<Button size="sm" onClick={onClose}>Close interview</Button>}
      >
        {data.status === "active" && (
          <div role="tablist" aria-label="How to answer" className="-mt-2 mb-4 flex border-b border-line">
            {tab("type", "Type answers")}
            {tab("voice", "Speak answers")}
          </div>
        )}
        {mode === "voice" && data.status === "active" ? (
          <VoicePanel interviewId={data.interview_id} onSaved={reload} />
        ) : (
          <TypedAnswer interview={data} onChange={reload} />
        )}
      </Card>

      <Card title="Transcript" description="Every answer, skip and addition in this interview, oldest first.">
        {data.transcript.length === 0 ? (
          <p className="text-sm text-muted">Nothing recorded yet.</p>
        ) : (
          <ol className="-m-4 divide-y divide-line">
            {data.transcript.map((t) => <TurnItem key={t.seq} turn={t} />)}
          </ol>
        )}
      </Card>
    </div>
  );
}

function InterviewForLeaver({ leaver }: { leaver: Person }) {
  const [id, setId] = useLocal(`kt.interview.${leaver.id}`);
  return id ? (
    <InterviewSession key={id} leaver={leaver} id={id} onClose={() => setId(null)} />
  ) : (
    <StartInterview leaver={leaver} onStarted={setId} />
  );
}

export function InterviewView() {
  return (
    <>
      <PageHeader
        title="Interview"
        description="An exit interview driven by the knowledge graph: it only asks about what the leaver alone knows, highest risk first."
      />
      <RequireLeaver>{(leaver) => <InterviewForLeaver leaver={leaver} />}</RequireLeaver>
    </>
  );
}
