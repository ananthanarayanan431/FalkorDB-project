"use client";

import { useState } from "react";

import { useApp } from "@/components/app-context";
import { Alert, Button, Card, ErrorAlert, Field, inputClass, PageHeader } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { clearLocal, writeLocal } from "@/lib/local-store";

const CONFIRM_WORD = "reset";

function ResetCard() {
  const { reloadPeople } = useApp();
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const disabledOnServer = error instanceof ApiError && error.status === 404;

  async function reset() {
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.reset();
      clearLocal("kt.interview.");
      writeLocal("kt.leaver", null);
      reloadPeople();
      setConfirm("");
      setDone(true);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="Delete all data"
      description="Removes every person, item, document and answer from the graph, and every interview transcript and saved handover plan from the database. This cannot be undone."
    >
      <div className="space-y-3">
        <Field label={`Type "${CONFIRM_WORD}" to confirm`} htmlFor="confirm-reset">
          <input
            id="confirm-reset"
            className={inputClass}
            autoComplete="off"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </Field>
        <Button variant="danger" onClick={reset} busy={busy} busyLabel="Deleting..." disabled={confirm.trim().toLowerCase() !== CONFIRM_WORD}>
          Delete all data
        </Button>
        {done && <Alert tone="ok">All data was deleted.</Alert>}
        {disabledOnServer ? (
          <Alert tone="warn" title="Reset is turned off on the server">
            The API has no authentication, so reset only works when the API server is started with
            ENABLE_RESET=true.
          </Alert>
        ) : (
          <ErrorAlert error={error} />
        )}
      </div>
    </Card>
  );
}

function BrowserCard() {
  const [cleared, setCleared] = useState(false);
  return (
    <Card
      title="This browser"
      description="This browser remembers which leaver you picked and the last interview for each leaver, so you can continue where you stopped. Nothing else is kept here."
    >
      <div className="space-y-3">
        <Button
          onClick={() => {
            clearLocal("kt.");
            setCleared(true);
          }}
        >
          Forget these choices
        </Button>
        {cleared && <Alert tone="ok">Cleared. The data on the server is unchanged.</Alert>}
      </div>
    </Card>
  );
}

export function SettingsView() {
  return (
    <>
      <PageHeader title="Settings" />
      <div className="max-w-2xl space-y-6">
        <BrowserCard />
        <ResetCard />
      </div>
    </>
  );
}
