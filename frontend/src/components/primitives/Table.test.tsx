import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { Table, type Column } from "./Table";

interface Row { id: string; name: string; kind: string; n: number | null }
const rows: Row[] = [
  { id: "1", name: "bravo", kind: "a", n: 2 },
  { id: "2", name: "alpha", kind: "b", n: null },
  { id: "3", name: "charlie", kind: "a", n: 10 },
];
const columns: Column<Row>[] = [
  { key: "name", header: "Name", sortValue: (r) => r.name, render: (r) => r.name },
  { key: "n", header: "N", align: "right", sortValue: (r) => r.n, render: (r) => r.n ?? "—" },
];
const names = () => screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0].textContent);

function setup() {
  render(
    <Table columns={columns} rows={rows} rowKey={(r) => r.id} searchText={(r) => r.name}
      filters={[{ label: "Kind", value: (r) => r.kind }]} />,
  );
}

afterEach(cleanup);

describe("Table", () => {
  it("sorts asc, desc, then back to original order; nulls sort last", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: "N" }));
    expect(names()).toEqual(["bravo", "charlie", "alpha"]);
    await userEvent.click(screen.getByRole("button", { name: "N" }));
    expect(names()).toEqual(["charlie", "bravo", "alpha"]);
    await userEvent.click(screen.getByRole("button", { name: "N" }));
    expect(names()).toEqual(["bravo", "alpha", "charlie"]);
  });

  it("searches and filters", async () => {
    setup();
    await userEvent.type(screen.getByLabelText("Search"), "ar");
    expect(names()).toEqual(["charlie"]);
    await userEvent.clear(screen.getByLabelText("Search"));
    await userEvent.selectOptions(screen.getByLabelText("Kind"), "b");
    expect(names()).toEqual(["alpha"]);
  });
});
