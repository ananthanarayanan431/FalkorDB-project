"use client";

import { useState, type FormEvent } from "react";

import { useApp } from "@/components/app-context";
import {
  Alert,
  Badge,
  Button,
  Card,
  cx,
  EmptyState,
  ErrorAlert,
  Field,
  inputClass,
  Loading,
  PageHeader,
} from "@/components/ui";
import { api } from "@/lib/api";
import { KNOWS_LEVEL_LABEL, plural, SENIORITY_LABEL } from "@/lib/format";
import type { Person, PersonStatus, Seniority } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

const EMPTY: Person = { id: "", name: "", role: "", seniority: "mid", status: "active" };

/** The id format the backend uses for slugs: lowercase letters, digits and hyphens. */
function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function PersonForm({ initial, onDone }: { initial: Person | null; onDone: () => void }) {
  const { people, reloadPeople } = useApp();
  const editing = initial !== null;
  const [form, setForm] = useState<Person>(initial ?? EMPTY);
  const [idTouched, setIdTouched] = useState(editing);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const clash = !editing && people.some((p) => p.id === form.id);

  function set<K extends keyof Person>(key: K, value: Person[K]) {
    setForm((f) => {
      const next = { ...f, [key]: value };
      if (key === "name" && !idTouched) next.id = slug(String(value));
      return next;
    });
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      await api.savePerson({ ...form, id: form.id.trim(), name: form.name.trim(), role: form.role.trim() });
      reloadPeople();
      setSaved(`${form.name} saved.`);
      if (!editing) {
        setForm(EMPTY);
        setIdTouched(false);
      } else {
        onDone();
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title={editing ? `Edit ${initial.name}` : "Add a person"}
      actions={editing && <Button size="sm" variant="ghost" onClick={onDone}>Cancel</Button>}
    >
      <form className="space-y-3" onSubmit={submit}>
        <Field label="Name" htmlFor="p-name">
          <input id="p-name" required className={inputClass} value={form.name} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field
          label="ID"
          htmlFor="p-id"
          hint={editing ? "The ID cannot be changed." : clash ? "A person with this ID exists; saving will update them." : "Used to link this person in imports. Filled in from the name."}
        >
          <input
            id="p-id"
            required
            readOnly={editing}
            className={cx(inputClass, "font-mono")}
            value={form.id}
            onChange={(e) => {
              setIdTouched(true);
              set("id", e.target.value);
            }}
          />
        </Field>
        <Field label="Role" htmlFor="p-role">
          <input id="p-role" className={inputClass} value={form.role} onChange={(e) => set("role", e.target.value)} placeholder="Backend Engineer" />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Seniority" htmlFor="p-seniority" hint="Decides the handover strategy.">
            <select id="p-seniority" className={inputClass} value={form.seniority} onChange={(e) => set("seniority", e.target.value as Seniority)}>
              {(Object.keys(SENIORITY_LABEL) as Seniority[]).map((s) => (
                <option key={s} value={s}>{SENIORITY_LABEL[s]}</option>
              ))}
            </select>
          </Field>
          <Field label="Status" htmlFor="p-status">
            <select id="p-status" className={inputClass} value={form.status} onChange={(e) => set("status", e.target.value as PersonStatus)}>
              <option value="active">Staying</option>
              <option value="leaving">Leaving</option>
            </select>
          </Field>
        </div>
        <Button type="submit" variant="primary" busy={busy} busyLabel="Saving..." disabled={!form.id.trim() || !form.name.trim()}>
          {editing ? "Save changes" : "Add person"}
        </Button>
        {saved && <Alert tone="ok">{saved}</Alert>}
        <ErrorAlert error={error} />
      </form>
    </Card>
  );
}

interface KnowsRow {
  key: number;
  item: string;
  level: number;
}

function KnowsForm() {
  const { people } = useApp();
  const graph = useAsync(api.graph, []);
  const items = (graph.data?.nodes ?? [])
    .filter((n) => n.labels.includes("Item"))
    .sort((a, b) => (a.name ?? a.id).localeCompare(b.name ?? b.id));
  const [person, setPerson] = useState("");
  const who = people.some((p) => p.id === person) ? person : (people[0]?.id ?? "");
  const [rows, setRows] = useState<KnowsRow[]>([{ key: 0, item: "", level: 2 }]);
  const [nextKey, setNextKey] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const filled = rows.filter((r) => r.item);

  function update(key: number, patch: Partial<KnowsRow>) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      const { updated } = await api.setKnows(who, filled.map(({ item, level }) => ({ item, level })));
      setSaved(`${plural(updated, "knowledge level")} saved for ${people.find((p) => p.id === who)?.name ?? who}.`);
      setRows([{ key: nextKey, item: "", level: 2 }]);
      setNextKey((k) => k + 1);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="What people already know"
      description="Handover plans leave out items a receiver knows at working level or better. Setting a level again replaces the old one."
    >
      {graph.error ? (
        <ErrorAlert error={graph.error} onRetry={graph.reload} />
      ) : !graph.data ? (
        <Loading />
      ) : items.length === 0 ? (
        <p className="text-sm text-muted">There are no items in the graph yet.</p>
      ) : (
        <form className="space-y-3" onSubmit={submit}>
          <Field label="Person" htmlFor="k-person">
            <select id="k-person" className={inputClass} value={who} onChange={(e) => setPerson(e.target.value)}>
              {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Items and levels</legend>
            {rows.map((r, i) => (
              <div key={r.key} className="flex flex-wrap gap-2">
                <select
                  aria-label={`Item ${i + 1}`}
                  className={cx(inputClass, "min-w-0 flex-[2_1_12rem]")}
                  value={r.item}
                  onChange={(e) => update(r.key, { item: e.target.value })}
                >
                  <option value="">Choose an item</option>
                  {items.map((n) => <option key={n.id} value={n.id}>{n.name ?? n.id}</option>)}
                </select>
                <select
                  aria-label={`Level for item ${i + 1}`}
                  className={cx(inputClass, "min-w-0 flex-[1_1_9rem]")}
                  value={r.level}
                  onChange={(e) => update(r.key, { level: Number(e.target.value) })}
                >
                  {[1, 2, 3].map((l) => <option key={l} value={l}>{KNOWS_LEVEL_LABEL[l]}</option>)}
                </select>
                {rows.length > 1 && (
                  <Button variant="ghost" onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}>Remove</Button>
                )}
              </div>
            ))}
            <Button
              size="sm"
              onClick={() => {
                setRows((rs) => [...rs, { key: nextKey, item: "", level: 2 }]);
                setNextKey((k) => k + 1);
              }}
            >
              Add another item
            </Button>
          </fieldset>
          <Button type="submit" variant="primary" busy={busy} busyLabel="Saving..." disabled={!who || filled.length === 0}>
            Save levels
          </Button>
          {saved && <Alert tone="ok">{saved}</Alert>}
          <ErrorAlert error={error} />
        </form>
      )}
    </Card>
  );
}

export function PeopleView() {
  const { people, peopleLoaded, peopleError, reloadPeople } = useApp();
  const [editing, setEditing] = useState<Person | null>(null);

  return (
    <>
      <PageHeader title="People" description="Everyone in the knowledge graph. Mark the person who is leaving, and set seniority so each receiver gets the right kind of plan." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="min-w-0 space-y-6">
          <Card title={peopleLoaded ? plural(people.length, "person", "people") : "People"}>
            {peopleError && !peopleLoaded ? (
              <ErrorAlert error={peopleError} onRetry={reloadPeople} />
            ) : !peopleLoaded ? (
              <Loading />
            ) : people.length === 0 ? (
              <EmptyState title="No people yet">Add someone with the form, or import data.</EmptyState>
            ) : (
              <div className="-m-4 overflow-x-auto">
                <table className="w-full min-w-[36rem] text-left text-sm">
                  <thead className="border-b border-line text-xs text-muted">
                    <tr>
                      <th scope="col" className="px-4 py-2 font-medium">Name</th>
                      <th scope="col" className="px-4 py-2 font-medium">Role</th>
                      <th scope="col" className="px-4 py-2 font-medium">Seniority</th>
                      <th scope="col" className="px-4 py-2 font-medium">Status</th>
                      <th scope="col" className="px-4 py-2"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {people.map((p) => (
                      <tr key={p.id}>
                        <td className="px-4 py-2.5">
                          <p className="font-medium">{p.name}</p>
                          <p className="font-mono text-xs text-muted">{p.id}</p>
                        </td>
                        <td className="px-4 py-2.5">{p.role}</td>
                        <td className="px-4 py-2.5">{SENIORITY_LABEL[p.seniority] ?? p.seniority}</td>
                        <td className="px-4 py-2.5">{p.status === "leaving" ? <Badge tone="warn">Leaving</Badge> : <Badge>Staying</Badge>}</td>
                        <td className="px-4 py-2.5 text-right">
                          <Button size="sm" onClick={() => setEditing(p)}>Edit</Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
          <KnowsForm />
        </div>
        <div className="min-w-0">
          <PersonForm key={editing?.id ?? "new"} initial={editing} onDone={() => setEditing(null)} />
        </div>
      </div>
    </>
  );
}
