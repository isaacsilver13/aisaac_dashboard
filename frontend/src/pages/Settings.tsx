import { useState, type FormEvent } from "react";

import { ConfigPanel } from "../components/ConfigPanel";
import { Card } from "../components/primitives/Card";
import { PageHeader } from "../components/primitives/PageHeader";
import { useTheme } from "../theme/useTheme";
import { readToken, writeToken } from "../token";

export default function Settings() {
  const { theme, toggle } = useTheme();
  const [saved, setSaved] = useState(() => readToken() !== "");
  const [draft, setDraft] = useState("");

  function save(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    writeToken(draft.trim());
    setDraft("");
    setSaved(true);
  }

  function clear() {
    writeToken("");
    setSaved(false);
  }

  return (
    <>
      <PageHeader title="Settings" />
      <div className="ui-stat-label" style={{ marginBottom: 8 }}>Access</div>
      <Card>
        <p style={{ margin: "0 0 12px" }}>
          The dashboard token unlocks Knowledge, financials, deployments and logs. It is stored in this browser only.
        </p>
        <form onSubmit={save} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            type="password"
            aria-label="Dashboard token"
            placeholder={saved ? "Token saved; enter a new one to replace it" : "Dashboard token"}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoComplete="off"
            style={{ flex: 1, minWidth: 220 }}
          />
          <button type="submit" disabled={!draft.trim()}>Save</button>
          {saved && <button type="button" onClick={clear}>Clear</button>}
        </form>
        <p className="ui-stat-label" style={{ marginTop: 12 }}>{saved ? "A token is saved." : "No token saved."}</p>
      </Card>

      {saved && (
        <>
          <div className="ui-stat-label" style={{ margin: "16px 0 8px" }}>Backend configuration</div>
          <ConfigPanel token={readToken()} />
        </>
      )}

      <div className="ui-stat-label" style={{ margin: "16px 0 8px" }}>Appearance</div>
      <Card>
        <button type="button" onClick={toggle}>Theme: {theme} (switch)</button>
      </Card>
    </>
  );
}
