import type { Metadata } from "next";

import { GapsView } from "@/views/gaps";

export const metadata: Metadata = { title: "Knowledge gaps" };

export default function Page() {
  return <GapsView />;
}
