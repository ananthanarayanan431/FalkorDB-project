"use client";

import { useEffect } from "react";

import { Button, ButtonLink, EmptyState } from "@/components/ui";

// Catches render errors in any page and keeps the header and navigation usable.
export default function ErrorPage({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <EmptyState
      title="Something went wrong on this page"
      action={
        <>
          <Button variant="primary" onClick={retry}>Try again</Button>
          <ButtonLink href="/">Go to the overview</ButtonLink>
        </>
      }
    >
      {error.message}
      {error.digest && <p className="mt-1 font-mono text-xs">Reference {error.digest}</p>}
    </EmptyState>
  );
}
