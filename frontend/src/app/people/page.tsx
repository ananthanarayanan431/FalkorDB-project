import type { Metadata } from "next";

import { PeopleView } from "@/views/people";

export const metadata: Metadata = { title: "People" };

export default function Page() {
  return <PeopleView />;
}
