import type { Metadata } from "next";

import { HandoverView } from "@/views/handover";

export const metadata: Metadata = { title: "Handover plans" };

export default function Page() {
  return <HandoverView />;
}
