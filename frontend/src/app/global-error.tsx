"use client";

import { useEffect } from "react";

import { Button, EmptyState } from "@/components/ui";
import { site } from "@/lib/site";
import "./globals.css";

// Replaces the root layout when it fails, so it renders its own document.
export default function GlobalError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex h-full items-center justify-center px-4 font-sans">
        <title>{`Error | ${site.name}`}</title>
        <main className="w-full max-w-md">
          <EmptyState title={`${site.name} could not load`} action={<Button variant="primary" onClick={retry}>Try again</Button>}>
            {error.digest ? `Reference ${error.digest}` : "Reload the page, or try again in a moment."}
          </EmptyState>
        </main>
      </body>
    </html>
  );
}
