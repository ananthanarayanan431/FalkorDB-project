const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

/** ISO strings (Postgres timestamps) or epoch milliseconds (graph timestamps). */
export function formatDateTime(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : dateTime.format(d);
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

export const SENIORITY_LABEL = { junior: "Junior", mid: "Mid-level", senior: "Senior" } as const;

export const STRATEGY_LABEL = {
  "foundations-first": "Foundations first",
  "delta-only": "Only what is new to them",
} as const;

export const KNOWS_LEVEL_LABEL: Record<number, string> = { 1: "Aware", 2: "Working knowledge", 3: "Expert" };

export const ANSWER_TYPE_LABEL: Record<string, string> = {
  rationale: "Rationale",
  trap: "Trap",
  procedure: "Procedure",
  contact: "Contact",
  other: "Other",
};

export const SOURCE_LABEL: Record<string, string> = {
  interview: "Typed interview",
  "interview-voice": "Voice interview",
  braindump: "Brain dump",
};
