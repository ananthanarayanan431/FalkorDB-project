"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import { cx } from "@/components/ui";

export interface TabItem<T extends string> {
  value: T;
  label: string;
}

/**
 * Tabs that follow the WAI-ARIA pattern: the tab row is one tab stop, the arrow keys, Home
 * and End move between tabs, and the panel holding `children` is labelled by the active tab.
 */
export function Tabs<T extends string>({
  label,
  items,
  value,
  onChange,
  className,
  children,
}: {
  label: string;
  items: readonly TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
  children: ReactNode;
}) {
  const id = useId();
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const tabId = (v: T) => `${id}-tab-${v}`;
  const panelId = `${id}-panel`;

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const current = items.findIndex((t) => t.value === value);
    const last = items.length - 1;
    const moves: Record<string, number> = {
      ArrowRight: current === last ? 0 : current + 1,
      ArrowLeft: current <= 0 ? last : current - 1,
      Home: 0,
      End: last,
    };
    const next = moves[e.key];
    if (next === undefined) return;
    e.preventDefault();
    onChange(items[next].value);
    tabs.current[next]?.focus();
  }

  return (
    <>
      <div role="tablist" aria-label={label} className={cx("flex border-b border-line", className)} onKeyDown={onKeyDown}>
        {items.map((t, i) => {
          const selected = t.value === value;
          return (
            <button
              key={t.value}
              ref={(el) => {
                tabs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={tabId(t.value)}
              aria-selected={selected}
              aria-controls={panelId}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(t.value)}
              className={cx(
                "border-b-2 px-3 py-2 text-sm",
                selected ? "border-accent font-medium text-accent" : "border-transparent text-muted hover:text-fg",
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={panelId} aria-labelledby={tabId(value)}>
        {children}
      </div>
    </>
  );
}
