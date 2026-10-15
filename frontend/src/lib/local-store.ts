"use client";

import { useCallback, useSyncExternalStore } from "react";

// Small per-browser preferences (selected leaver, last interview id). Never anything that
// must be shared or kept: that lives in the backend. Storage can be unavailable (private
// mode, blocked site data), so every access is guarded and the UI works without it.

const EVENT = "kt-local-store";

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeLocal(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Storage unavailable: the value just is not remembered.
  }
  window.dispatchEvent(new Event(EVENT));
}

export function clearLocal(prefix: string): void {
  try {
    const keys = Object.keys(window.localStorage).filter((k) => k.startsWith(prefix));
    keys.forEach((k) => window.localStorage.removeItem(k));
  } catch {
    // Nothing to clear.
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** A localStorage value as React state. `null` on the server and when unset. */
export function useLocal(key: string | null): [string | null, (value: string | null) => void] {
  const value = useSyncExternalStore(
    subscribe,
    () => (key ? read(key) : null),
    () => null,
  );
  const set = useCallback((v: string | null) => key && writeLocal(key, v), [key]);
  return [value, set];
}
