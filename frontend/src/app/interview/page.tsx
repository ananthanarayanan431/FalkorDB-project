import type { Metadata } from "next";

import { InterviewView } from "@/views/interview";

export const metadata: Metadata = { title: "Interview" };

export default function Page() {
  return <InterviewView />;
}
