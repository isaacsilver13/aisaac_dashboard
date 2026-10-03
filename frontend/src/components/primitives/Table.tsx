import { useMemo, useState, type ReactNode } from "react";
import { NavArrowDown, NavArrowUp } from "iconoir-react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  /** Makes the column sortable. Return a number or string; null sorts last. */
  sortValue?: (row: T) => string | number | null;
  align?: "left" | "right";
}

export interface TableFilter<T> {
  label: string;
  value: (row: T) => string;
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** Free-text search across this string; omit to hide the search box. */
  searchText?: (row: T) => string;
  /** Each filter becomes a dropdown of the distinct values found in `rows`. */
  filters?: TableFilter<T>[];
  emptyMessage?: string;
}

type Sort = { key: string; dir: "asc" | "desc" } | null;

/** Nulls always sort last, whichever direction is active. */
function compare(a: string | number | null, b: string | number | null, sign: number): number {
  if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
  return sign * (typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b)));
}

export function Table<T>({ columns, rows, rowKey, searchText, filters = [], emptyMessage = "No results." }: TableProps<T>) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<Sort>(null);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    let out = rows.filter(
      (row) =>
        (!needle || searchText?.(row).toLowerCase().includes(needle)) &&
        filters.every((f) => !selected[f.label] || f.value(row) === selected[f.label]),
    );
    const column = columns.find((c) => c.key === sort?.key);
    if (sort && column?.sortValue) {
      const sign = sort.dir === "asc" ? 1 : -1;
      const value = column.sortValue;
      out = [...out].sort((a, b) => compare(value(a), value(b), sign));
    }
    return out;
  }, [rows, query, selected, sort, columns, filters, searchText]);

  function toggleSort(key: string) {
    setSort((prev) => (prev?.key !== key ? { key, dir: "asc" } : prev.dir === "asc" ? { key, dir: "desc" } : null));
  }

  return (
    <div className="ui-table-wrap">
      {(searchText || filters.length > 0) && (
        <div className="ui-table-toolbar">
          {searchText && (
            <input type="search" placeholder="Search" aria-label="Search" value={query} onChange={(e) => setQuery(e.target.value)} />
          )}
          {filters.map((f) => (
            <select
              key={f.label}
              aria-label={f.label}
              value={selected[f.label] ?? ""}
              onChange={(e) => setSelected((prev) => ({ ...prev, [f.label]: e.target.value }))}
            >
              <option value="">{f.label}: all</option>
              {[...new Set(rows.map(f.value))].sort().map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          ))}
        </div>
      )}
      <div className="ui-table-scroll">
        <table className="ui-table">
          <thead>
            <tr>
              {columns.map((c) => {
                const active = sort?.key === c.key ? sort.dir : null;
                return (
                  <th
                    key={c.key}
                    className={c.align === "right" ? "ui-table-right" : undefined}
                    aria-sort={active ? (active === "asc" ? "ascending" : "descending") : c.sortValue ? "none" : undefined}
                  >
                    {c.sortValue ? (
                      <button type="button" className="ui-table-sort" onClick={() => toggleSort(c.key)}>
                        {c.header}
                        {active === "asc" && <NavArrowUp width={12} height={12} aria-hidden="true" />}
                        {active === "desc" && <NavArrowDown width={12} height={12} aria-hidden="true" />}
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((c) => (
                  <td key={c.key} className={c.align === "right" ? "ui-table-right" : undefined}>{c.render(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {visible.length === 0 && <p className="ui-table-empty">{emptyMessage}</p>}
      </div>
    </div>
  );
}
