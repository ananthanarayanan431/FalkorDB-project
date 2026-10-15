"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

export interface AsyncState<T> {
  data: T | undefined;
  error: unknown;
  /** True until the request for the current `deps` has settled. */
  loading: boolean;
  reload: () => void;
}

interface Settled<T> {
  query: string;
  run: number;
  data?: T;
  error?: unknown;
}

/**
 * Run `fn` whenever `deps` change (or `reload()` is called) and keep the latest result.
 * `deps` must be JSON-serialisable. Pass `enabled: false` to skip the request.
 *
 * While a reload of the same query runs, the previous `data` stays visible; after `deps`
 * change it is cleared, so a page never shows one leaver's data under another's name.
 * With Cache Components a hidden route's effects re-run when it is shown again, so
 * data is refetched when the user comes back to a page.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], enabled = true): AsyncState<T> {
  const [nonce, setNonce] = useState(0);
  const query = JSON.stringify(deps);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const call = useEffectEvent(fn);

  useEffect(() => {
    if (!enabled) return;
    let live = true;
    call().then(
      (data) => live && setSettled({ query, run: nonce, data }),
      (error: unknown) =>
        live && setSettled((s) => ({ query, run: nonce, error, data: s?.query === query ? s.data : undefined })),
    );
    return () => {
      live = false;
    };
  }, [enabled, query, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const sameQuery = enabled && settled?.query === query;
  return {
    data: sameQuery ? settled.data : undefined,
    error: sameQuery && settled.run === nonce ? settled.error : undefined,
    loading: enabled && !(sameQuery && settled.run === nonce),
    reload,
  };
}
