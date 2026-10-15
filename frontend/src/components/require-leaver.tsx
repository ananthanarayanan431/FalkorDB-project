"use client";

import type { ReactNode } from "react";

import { useApp } from "@/components/app-context";
import { ButtonLink, EmptyState, ErrorAlert, Loading } from "@/components/ui";
import type { Person } from "@/lib/types";

/** Renders `children` once there is a leaver to work on, otherwise explains what to do. */
export function RequireLeaver({ children }: { children: (leaver: Person) => ReactNode }) {
  const { people, peopleLoaded, peopleError, reloadPeople, leaver } = useApp();
  if (peopleError && !peopleLoaded) return <ErrorAlert error={peopleError} onRetry={reloadPeople} />;
  if (!peopleLoaded) return <Loading />;
  if (people.length === 0) {
    return (
      <EmptyState
        title="No people in the graph yet"
        action={<ButtonLink href="/import" variant="primary">Import data</ButtonLink>}
      >
        Load the demo company or import your own sources first.
      </EmptyState>
    );
  }
  if (!leaver) {
    return (
      <EmptyState
        title="No leaver selected"
        action={<ButtonLink href="/people">Go to People</ButtonLink>}
      >
        Pick a person in the Leaver menu at the top of the page, or set someone&apos;s status to
        leaving on the People page.
      </EmptyState>
    );
  }
  return <>{children(leaver)}</>;
}
