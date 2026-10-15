import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { ApiError } from "@/lib/api";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ---- buttons ---------------------------------------------------------------

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANT: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg border-accent hover:opacity-90",
  secondary: "bg-surface text-fg border-line hover:bg-surface-2",
  danger: "bg-danger text-white border-danger hover:opacity-90 dark:text-bg",
  ghost: "bg-transparent text-fg border-transparent hover:bg-surface-2",
};

export function buttonClass(variant: Variant = "secondary", size: "sm" | "md" = "md"): string {
  return cx(
    "inline-flex items-center justify-center gap-2 rounded-md border font-medium whitespace-nowrap",
    "disabled:cursor-not-allowed disabled:opacity-50",
    size === "sm" ? "px-2.5 py-1 text-sm" : "px-3.5 py-2 text-sm",
    VARIANT[variant],
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  /** Shows `busyLabel` and disables the button while an action runs. */
  busy?: boolean;
  busyLabel?: string;
}

export function Button({ variant, size, busy, busyLabel, className, disabled, children, type, ...rest }: ButtonProps) {
  return (
    <button
      type={type ?? "button"}
      className={cx(buttonClass(variant, size), className)}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? (busyLabel ?? "Working...") : children}
    </button>
  );
}

export function ButtonLink({ href, variant, size, children }: { href: string; variant?: Variant; size?: "sm" | "md"; children: ReactNode }) {
  return (
    <Link href={href} className={buttonClass(variant, size)}>
      {children}
    </Link>
  );
}

// ---- layout ----------------------------------------------------------------

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0 max-w-2xl">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function Card({
  title,
  description,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-lg border border-line bg-surface", className)}>
      {(title || actions) && (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

// ---- status ----------------------------------------------------------------

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger";

const BADGE: Record<Tone, string> = {
  neutral: "border-line bg-surface-2 text-muted",
  accent: "border-accent/40 bg-accent-soft text-accent",
  ok: "border-ok/40 bg-ok-soft text-ok",
  warn: "border-warn/40 bg-warn-soft text-warn",
  danger: "border-danger/40 bg-danger-soft text-danger",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={cx("inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap", BADGE[tone])}>
      {children}
    </span>
  );
}

const ALERT: Record<Exclude<Tone, "neutral">, string> = {
  accent: "border-accent/40 bg-accent-soft",
  ok: "border-ok/40 bg-ok-soft",
  warn: "border-warn/40 bg-warn-soft",
  danger: "border-danger/40 bg-danger-soft",
};

export function Alert({ tone = "accent", title, children, action }: { tone?: Exclude<Tone, "neutral">; title?: ReactNode; children?: ReactNode; action?: ReactNode }) {
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={cx("rounded-md border px-3 py-2.5 text-sm", ALERT[tone])}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          {title && <p className="font-medium">{title}</p>}
          {children && <div className={cx(Boolean(title) && "mt-0.5", "text-fg/90")}>{children}</div>}
        </div>
        {action}
      </div>
    </div>
  );
}

/** Renders any error, with the field-level details the API sends for validation failures. */
export function ErrorAlert({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  const fields = error instanceof ApiError ? error.fieldErrors : [];
  return (
    <Alert
      tone="danger"
      title={message}
      action={onRetry && <Button size="sm" onClick={onRetry}>Try again</Button>}
    >
      {fields.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          {fields.slice(0, 20).map((f, i) => (
            <li key={i}>
              <code className="font-mono text-xs">{f.field}</code>: {f.message}
            </li>
          ))}
          {fields.length > 20 && <li>and {fields.length - 20} more</li>}
        </ul>
      )}
    </Alert>
  );
}

export function Loading({ label = "Loading..." }: { label?: string }) {
  return <p className="text-sm text-muted" role="status">{label}</p>;
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</div>}
      {action && <div className="mt-4 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function Stat({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2.5">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-0.5 text-xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-0.5 text-xs text-muted">{note}</p>}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-2 w-full overflow-hidden rounded-sm bg-surface-2"
    >
      <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
    </div>
  );
}

// ---- forms -----------------------------------------------------------------

export const inputClass =
  "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-fg placeholder:text-muted/70 disabled:opacity-60";

export function Field({ label, htmlFor, hint, children }: { label: string; htmlFor: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="block text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}
