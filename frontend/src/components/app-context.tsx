"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { api } from "@/lib/api";
import { useLocal } from "@/lib/local-store";
import type { Health, Person } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

interface AppState {
  people: Person[];
  peopleLoaded: boolean;
  peopleError: unknown;
  reloadPeople: () => void;
  /** The leaver every page works on: the one picked in the header, else the first marked leaving. */
  leaver: Person | null;
  setLeaverId: (id: string | null) => void;
  health: Health | undefined;
  healthError: unknown;
  reloadHealth: () => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const people = useAsync(api.people, []);
  const health = useAsync(api.health, []);
  const [picked, setPicked] = useLocal("kt.leaver");

  const value = useMemo<AppState>(() => {
    const list = people.data ?? [];
    const leaver =
      list.find((p) => p.id === picked) ?? list.find((p) => p.status === "leaving") ?? null;
    return {
      people: list,
      peopleLoaded: people.data !== undefined,
      peopleError: people.error,
      reloadPeople: people.reload,
      leaver,
      setLeaverId: setPicked,
      health: health.data,
      healthError: health.error,
      reloadHealth: health.reload,
    };
  }, [people.data, people.error, people.reload, picked, setPicked, health.data, health.error, health.reload]);

  return <AppContext value={value}>{children}</AppContext>;
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside <AppProvider>");
  return ctx;
}
