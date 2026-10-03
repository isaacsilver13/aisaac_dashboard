import { useCallback } from "react";

import { fetchConfigStatus } from "../api";
import { useAsyncData } from "../hooks/useAsyncData";
import type { ConfigItem } from "../types";
import { ErrorState } from "./primitives/ErrorState";
import { StatusDot } from "./primitives/StatusDot";
import { Table, type Column } from "./primitives/Table";

const columns: Column<ConfigItem>[] = [
  { key: "label", header: "Setting", sortValue: (c) => c.label, render: (c) => c.label },
  {
    key: "configured",
    header: "Status",
    sortValue: (c) => (c.configured ? 1 : 0),
    render: (c) => (
      <>
        <StatusDot tone={c.configured ? "success" : "warning"} label={c.configured ? "set" : "not set"} />{" "}
        {c.configured ? "Set" : "Not set"}
      </>
    ),
  },
  { key: "used", header: "Used for", render: (c) => c.used_for },
];

/** Shows whether each backend secret/setting is configured; never the values. */
export function ConfigPanel({ token }: { token: string }) {
  const { data, loading, error, reload } = useAsyncData(useCallback(() => fetchConfigStatus(token), [token]));
  if (error) return <ErrorState message={error} onRetry={() => void reload()} />;
  if (loading || !data) return null;
  return <Table columns={columns} rows={data} rowKey={(c) => c.key} />;
}
