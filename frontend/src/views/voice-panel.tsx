"use client";

import { useEffect, useRef, useState } from "react";

import { useApp } from "@/components/app-context";
import { Alert, Badge, Button, cx } from "@/components/ui";
import { ANSWER_TYPE_LABEL } from "@/lib/format";
import { VoiceClient, type VoiceEvent, type VoiceState } from "@/lib/voice";

interface LogEntry {
  id: number;
  kind: "agent" | "user" | "note" | "error";
  label: string;
  text: string;
}

const STATE_LABEL: Record<VoiceState, string> = {
  connecting: "Connecting",
  speaking: "Agent speaking",
  listening: "Listening",
  processing: "Saving your answer",
  ended: "Interview ended",
  closed: "Not connected",
};

export function VoicePanel({ interviewId, onSaved }: { interviewId: string; onSaved: () => void }) {
  const { health } = useApp();
  const client = useRef<VoiceClient | null>(null);
  const nextId = useRef(0);
  const [state, setState] = useState<VoiceState>("closed");
  const [log, setLog] = useState<LogEntry[]>([]);

  // Release the microphone and socket when the page is left or hidden, or the interview changes.
  useEffect(
    () => () => {
      client.current?.stop();
      client.current = null;
    },
    [interviewId],
  );

  function add(kind: LogEntry["kind"], label: string, text: string) {
    const id = nextId.current++;
    setLog((l) => [...l, { id, kind, label, text }]);
  }

  function onEvent(e: VoiceEvent) {
    switch (e.type) {
      case "transcript":
        add(e.role, e.role === "agent" ? "Agent" : e.amend ? "You (added to last answer)" : "You", e.text);
        break;
      case "saved":
        add(
          "note",
          "Saved",
          `Answer stored for ${e.item_id} as ${ANSWER_TYPE_LABEL[e.answer_type] ?? e.answer_type}` +
            (e.new_items.length ? `. New items: ${e.new_items.join(", ")}` : ""),
        );
        onSaved();
        break;
      case "clear":
        add("note", "Interrupted", "The agent stopped talking so you could answer.");
        break;
      case "error":
        add("error", "Error", e.message);
        break;
      case "ended":
        add("note", "Ended", e.reason === "complete" ? "The interview is finished." : e.reason);
        onSaved();
        break;
    }
  }

  function start() {
    client.current?.stop();
    setLog([]);
    const c = new VoiceClient(interviewId, {
      onEvent,
      onState: setState,
      onError: (message) => add("error", "Error", message),
    });
    client.current = c;
    void c.start();
  }

  function stop() {
    client.current?.stop();
    client.current = null;
  }

  const active = state !== "closed" && state !== "ended";

  if (health?.llm === false) {
    return (
      <Alert tone="warn" title="Voice is not available">
        Voice interviews use speech recognition and speech synthesis through OpenRouter. Set
        OPENROUTER_API_KEY on the API server to turn them on.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Alert tone="accent" title="Before you start">
        Use headphones, otherwise the agent can hear itself and stop mid-sentence. Speak over the
        agent to interrupt it. You can say &quot;skip&quot;, &quot;repeat that&quot;, &quot;hold
        on&quot; or &quot;stop&quot;. Works in current Chrome and Edge.
      </Alert>
      <div className="flex flex-wrap items-center gap-3">
        {active ? (
          <Button variant="danger" onClick={stop}>End voice session</Button>
        ) : (
          <Button variant="primary" onClick={start}>Start speaking</Button>
        )}
        <span role="status" aria-live="polite">
          <Badge tone={state === "listening" ? "ok" : state === "speaking" ? "accent" : "neutral"}>
            {STATE_LABEL[state]}
          </Badge>
        </span>
      </div>
      {log.length > 0 && (
        <ol className="space-y-2" aria-live="polite">
          {log.map((m) => (
            <li
              key={m.id}
              className={cx(
                "rounded-md border px-3 py-2 text-sm",
                m.kind === "agent" && "mr-8 border-line bg-surface",
                m.kind === "user" && "ml-8 border-accent/40 bg-accent-soft",
                m.kind === "note" && "border-dashed border-line text-muted",
                m.kind === "error" && "border-danger/40 bg-danger-soft",
              )}
            >
              <p className="text-xs font-medium text-muted">{m.label}</p>
              <p className="mt-0.5 whitespace-pre-wrap">{m.text}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
