import type { Metadata } from "next";

import { ImportView } from "@/views/import";

export const metadata: Metadata = { title: "Import data" };

export default function Page() {
  return <ImportView />;
}
