import type { Metadata } from "next";

import { GraphView } from "@/views/graph";

export const metadata: Metadata = { title: "Graph data" };

export default function Page() {
  return <GraphView />;
}
