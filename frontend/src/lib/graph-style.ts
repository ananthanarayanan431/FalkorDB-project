import type { PropertyValue, RawNode } from "./types";

// One fixed colour per label used by this app, readable on light and dark backgrounds.
// Labels the app does not know get a colour from FALLBACK, picked by name so it is stable.
export const LABEL_COLOR: Record<string, string> = {
  Person: "#2f7d6b",
  System: "#3b6ea5",
  Decision: "#b7791f",
  Topic: "#6b8e23",
  Item: "#5a7184",
  Document: "#8a6a4f",
  Answer: "#b04a3a",
};

const FALLBACK = ["#4f6d7a", "#7a5c4f", "#5d7a4f", "#7a6a2f", "#2f6a7a", "#7a4f4f"];

/** The label that decides a node's colour: the most specific one this app knows, else the first. */
const PRIORITY = ["Person", "Decision", "System", "Topic", "Item", "Document", "Answer"];

export function primaryLabel(labels: string[]): string {
  return PRIORITY.find((l) => labels.includes(l)) ?? labels[0] ?? "Node";
}

export function labelColor(label: string): string {
  if (LABEL_COLOR[label]) return LABEL_COLOR[label];
  let h = 0;
  for (const ch of label) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return FALLBACK[h % FALLBACK.length];
}

function short(text: string, max = 40): string {
  return text.length > max ? `${text.slice(0, max - 3)}...` : text;
}

/** What to write next to a node: its name or title, an answer's text, else its id. */
export function caption(node: RawNode): string {
  const p = node.properties;
  for (const key of ["name", "title"]) {
    if (typeof p[key] === "string" && p[key]) return short(p[key] as string);
  }
  if (typeof p.text === "string" && p.text) return short(p.text);
  if (p.id !== undefined && p.id !== null) return short(String(p.id));
  return `#${node.id}`;
}

/** Epoch milliseconds stored under keys like created_at are shown as dates too. */
export function formatProperty(key: string, value: PropertyValue): string {
  if (value === null) return "null";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "number" && key.endsWith("_at") && value > 1e11) {
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) return `${value} (${d.toLocaleString()})`;
  }
  return String(value);
}

/** Case-insensitive match on the caption, id and every property value. */
export function nodeMatches(node: RawNode, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return false;
  if (caption(node).toLowerCase().includes(q) || String(node.id) === q) return true;
  return Object.values(node.properties).some((v) => v !== null && String(v).toLowerCase().includes(q));
}
