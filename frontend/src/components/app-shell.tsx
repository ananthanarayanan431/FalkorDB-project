"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { useApp } from "@/components/app-context";
import { cx, inputClass } from "@/components/ui";
import { site } from "@/lib/site";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/import", label: "Import data" },
  { href: "/gaps", label: "Knowledge gaps" },
  { href: "/interview", label: "Interview" },
  { href: "/handover", label: "Handover plans" },
  { href: "/people", label: "People" },
  { href: "/graph", label: "Graph" },
  { href: "/settings", label: "Settings" },
];

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main">
      <ul className="space-y-0.5">
        {NAV.map(({ href, label }) => {
          const active = isActive(pathname, href);
          return (
            <li key={href}>
              <Link
                href={href}
                onNavigate={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "block rounded-md px-3 py-2 text-sm",
                  active ? "bg-accent-soft font-medium text-accent" : "text-fg hover:bg-surface-2",
                )}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function LeaverPicker() {
  const { people, peopleLoaded, leaver, setLeaverId } = useApp();
  if (!peopleLoaded || people.length === 0) return null;
  return (
    <div className="flex min-w-0 items-center gap-2">
      <label htmlFor="leaver-picker" className="text-sm text-muted">
        Leaver
      </label>
      <select
        id="leaver-picker"
        className={cx(inputClass, "w-auto max-w-[14rem] py-1.5")}
        value={leaver?.id ?? ""}
        onChange={(e) => setLeaverId(e.target.value || null)}
      >
        {!leaver && <option value="">Choose a person</option>}
        {people.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
            {p.status === "leaving" ? " (leaving)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="flex min-h-full flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-20 border-b border-line bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-md border border-line px-2.5 py-1 text-sm lg:hidden"
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
              onClick={() => setMenuOpen((o) => !o)}
            >
              {menuOpen ? "Close" : "Menu"}
            </button>
            <Link href="/" className="flex items-center gap-2 font-semibold">
              {/* eslint-disable-next-line @next/next/no-img-element -- static SVG mark, no optimisation needed */}
              <img src="/icon.svg" alt="" width={22} height={22} />
              {site.name}
            </Link>
          </div>
          <LeaverPicker />
        </div>
        {menuOpen && (
          <div id="mobile-nav" className="border-t border-line px-4 py-2 lg:hidden">
            <Nav onNavigate={() => setMenuOpen(false)} />
          </div>
        )}
      </header>

      <div className="mx-auto flex w-full max-w-7xl flex-1 gap-8 px-4">
        <aside className="hidden w-52 shrink-0 py-6 lg:block">
          <div className="sticky top-20">
            <Nav />
          </div>
        </aside>
        <main id="main" className="min-w-0 flex-1 py-6">
          {children}
        </main>
      </div>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 text-sm text-muted">
          <p>{site.name}</p>
          <ul className="flex flex-wrap gap-4">
            <li><Link className="hover:text-fg hover:underline" href="/privacy">Privacy policy</Link></li>
            <li><Link className="hover:text-fg hover:underline" href="/terms">Terms and conditions</Link></li>
            <li><a className="hover:text-fg hover:underline" href="/docs">API reference</a></li>
          </ul>
        </div>
      </footer>
    </div>
  );
}
