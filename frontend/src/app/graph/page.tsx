import type { Metadata } from "next";

import { GraphView } from "@/views/graph-explorer";

export const metadata: Metadata = { title: "Graph" };

export default function Page() {
  return <GraphView />;
}
