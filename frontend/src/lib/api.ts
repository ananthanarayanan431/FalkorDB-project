// Typed client for the FastAPI backend. Every response is an envelope:
//   {"success": true,  "message", "data"}
//   {"success": false, "message", "error": {"code", "details"}}

import type {
  AnswerResult,
  BrainDumpResult,
  Coverage,
  Gap,
  GraphExport,
  Health,
  IngestCounts,
  Interview,
  InterviewStarted,
  Person,
  Plan,
  SavedPlan,
  SavedPlanSummary,
  SkipResult,
} from "./types";

const BASE = "/api/v1";

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly details: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Validation details as field/message pairs, when the backend sent them. */
  get fieldErrors(): FieldError[] {
    if (!Array.isArray(this.details)) return [];
    return this.details.filter(
      (d): d is FieldError => typeof d?.field === "string" && typeof d?.message === "string",
    );
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

function url(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== null && v !== undefined && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function request<T>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(url(path, query), {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Could not reach the server. Check that the API is running.", 0, "NETWORK_ERROR");
  }
  let payload: { success?: boolean; message?: string; data?: T; error?: { code?: string; details?: unknown } };
  try {
    payload = await resp.json();
  } catch {
    throw new ApiError(`The server returned an unreadable response (HTTP ${resp.status}).`, resp.status, "BAD_RESPONSE");
  }
  if (!resp.ok || payload.success === false) {
    throw new ApiError(
      payload.message ?? `Request failed (HTTP ${resp.status})`,
      resp.status,
      payload.error?.code ?? "HTTP_ERROR",
      payload.error?.details ?? null,
    );
  }
  return payload.data as T;
}

export const api = {
  health: () => request<Health>("GET", "/health"),

  people: () => request<Person[]>("GET", "/people"),
  savePerson: (p: Person) => request<Person>("POST", "/people", p),
  setKnows: (person: string, knows: { item: string; level: number }[]) =>
    request<{ updated: number }>("PUT", `/people/${encodeURIComponent(person)}/knows`, knows),

  seed: () => request<IngestCounts>("POST", "/ingest/seed"),
  ingestSources: (bundle: unknown) => request<IngestCounts>("POST", "/ingest/sources", bundle),
  brainDump: (person: string, text: string) =>
    request<BrainDumpResult>("POST", "/ingest/braindump", { person, text }),

  gaps: (leaver: string | null, onlyOpen: boolean) =>
    request<Gap[]>("GET", "/gaps", undefined, { leaver, only_open: onlyOpen }),
  coverage: (leaver: string | null) => request<Coverage>("GET", "/coverage", undefined, { leaver }),
  graph: () => request<GraphExport>("GET", "/graph"),

  startInterview: (leaver: string | null) => request<InterviewStarted>("POST", "/interviews", { leaver }),
  interview: (id: string) => request<Interview>("GET", `/interviews/${encodeURIComponent(id)}`),
  answer: (id: string, answer: string) =>
    request<AnswerResult>("POST", `/interviews/${encodeURIComponent(id)}/answer`, { answer }),
  skip: (id: string) => request<SkipResult>("POST", `/interviews/${encodeURIComponent(id)}/skip`),

  previewPlan: (receiver: string, leaver: string | null) =>
    request<Plan>("GET", `/handover/${encodeURIComponent(receiver)}`, undefined, { leaver }),
  savePlan: (receiver: string, leaver: string | null) =>
    request<SavedPlan>("POST", "/handover-plans", { receiver, leaver }),
  plans: (filter: { leaver?: string | null; receiver?: string | null; limit?: number }) =>
    request<SavedPlanSummary[]>("GET", "/handover-plans", undefined, filter),
  plan: (id: string) => request<SavedPlan>("GET", `/handover-plans/${encodeURIComponent(id)}`),

  reset: () => request<null>("POST", "/reset"),
};

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
