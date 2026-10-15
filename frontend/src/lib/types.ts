// Shapes returned by the FastAPI backend (knowledge_transfer/api). Keep in sync with it.

export type Seniority = "junior" | "mid" | "senior";
export type PersonStatus = "active" | "leaving";
export type ItemKind = "system" | "decision" | "topic";

export interface Person {
  id: string;
  name: string;
  role: string;
  seniority: Seniority;
  status: PersonStatus;
}

export interface Health {
  status: string;
  graph: "up" | "down";
  database: "up" | "down";
  llm: boolean;
}

export interface Gap {
  item_id: string;
  name: string;
  kind: ItemKind;
  description: string;
  sole_owner: boolean;
  undocumented: boolean;
  dependents: number;
  answers: number;
  risk: number;
  reasons: string[];
  open: boolean;
}

export interface Coverage {
  leaver: string;
  unique_items: number;
  covered: number;
  open: number;
  percent: number;
  risk_weighted_percent: number;
  items: Gap[];
}

export interface GraphNode {
  id: string;
  labels: string[];
  name: string | null;
  status: string | null;
}

export interface GraphEdge {
  src: string;
  rel: string;
  dst: string;
}

export interface GraphExport {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/** A property value as FalkorDB returns it. */
export type PropertyValue = string | number | boolean | null | PropertyValue[] | { [key: string]: PropertyValue };

/** A node exactly as stored in FalkorDB. `id` is the internal id, valid within one read. */
export interface RawNode {
  id: number;
  labels: string[];
  properties: Record<string, PropertyValue>;
}

export interface RawEdge {
  id: number;
  source: number;
  target: number;
  type: string;
  properties: Record<string, PropertyValue>;
}

export interface GraphSnapshot {
  nodes: RawNode[];
  edges: RawEdge[];
  truncated: boolean;
}

export interface GraphSchema {
  node_count: number;
  edge_count: number;
  labels: { label: string; count: number }[];
  relationship_types: { type: string; count: number }[];
}

export interface Question {
  item_id: string;
  item_name: string;
  text: string;
  reasons: string[];
  risk: number;
  is_follow_up: boolean;
}

export interface InterviewStarted {
  interview_id: string;
  leaver: string;
  question: Question | null;
}

export interface Turn {
  seq: number;
  action: "answer" | "skip" | "amend";
  item_id: string;
  question: string;
  answer: string | null;
  answer_type: string | null;
  is_follow_up: boolean;
  new_items: string[];
  created_at: string;
}

export interface Interview {
  interview_id: string;
  leaver: string;
  status: "active" | "completed";
  turns: number;
  question: Question | null;
  transcript: Turn[];
}

export interface AnswerResult {
  stored_for: string;
  answer_type: string;
  new_items: string[];
  next_question: Question | null;
}

export interface SkipResult {
  next_question: Question | null;
}

export interface PlanKnowledge {
  text: string;
  kind: string;
  source: string;
  created_at: number; // epoch milliseconds
}

export interface PlanStep {
  order: number;
  item_id: string;
  name: string;
  kind: ItemKind;
  mode: "read" | "learn";
  why_included: string;
  description: string;
  knowledge: PlanKnowledge[];
  read: string[];
  learn_first: string[];
  risk: number;
}

export interface Plan {
  receiver: { id: string; name: string; role: string; seniority: Seniority };
  leaver: string;
  strategy: "foundations-first" | "delta-only";
  summary: string;
  skipped_already_known: number;
  steps: PlanStep[];
}

export interface SavedPlanSummary {
  id: string;
  leaver: string;
  receiver: string;
  strategy: Plan["strategy"];
  summary: string;
  step_count: number;
  created_at: string;
}

export interface SavedPlan extends SavedPlanSummary {
  plan: Plan;
}

export interface IngestCounts {
  people: number;
  items: number;
  documents: number;
  contributions: number;
  links: number;
  knows: number;
}

export interface BrainDumpResult {
  items_found: number;
  new_items: string[];
}
