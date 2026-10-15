import type { ReactNode } from "react";

import { site } from "@/lib/site";

export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="max-w-3xl">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      {site.policyDate && <p className="mt-1 text-sm text-muted">Effective {site.policyDate}</p>}
      <div className="mt-6 space-y-6 text-sm leading-relaxed [&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_li]:mt-1 [&_ul]:list-disc [&_ul]:pl-5">
        {children}
      </div>
    </article>
  );
}
