import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import type { VaultGraph } from "../../types";
import { Graph } from "./Graph";

afterEach(cleanup);

const graph: VaultGraph = {
  nodes: [
    { path: "wikis/a.md", title: "Alpha", folder: "wikis" },
    { path: "wikis/b.md", title: "Beta", folder: "wikis" },
    { path: "projects/c.md", title: "Gamma", folder: "projects" },
  ],
  edges: [
    ["wikis/a.md", "wikis/b.md"],
    ["projects/c.md", "wikis/a.md"],
  ],
};
const renderIt = (props: Partial<Parameters<typeof Graph>[0]> = {}) =>
  render(
    <MemoryRouter>
      <Graph graph={graph} {...props} />
    </MemoryRouter>,
  );
const circles = (container: HTMLElement) => [...container.querySelectorAll("circle")];
const hidden = (el: Element) => (el as SVGElement).style.display === "none";

describe("Graph", () => {
  it("draws every note and link with a folder filter legend", () => {
    const { container } = renderIt();
    expect(circles(container)).toHaveLength(3);
    expect(container.querySelectorAll("line")).toHaveLength(2);
    expect(screen.getByRole("checkbox", { name: "wikis" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "projects" })).toBeChecked();
  });

  it("hides a folder's nodes and their links when its toggle is unchecked", () => {
    const { container } = renderIt();
    fireEvent.click(screen.getByRole("checkbox", { name: "projects" }));
    expect(circles(container).filter(hidden)).toHaveLength(1);
    expect([...container.querySelectorAll("line")].filter(hidden)).toHaveLength(1);
  });

  it("dims notes that do not match the search", () => {
    const { container } = renderIt();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "beta" } });
    const dimmed = circles(container).filter((c) => c.classList.contains("dim"));
    expect(dimmed).toHaveLength(2);
  });

  it("dims everything but the hovered note and its neighbours", () => {
    const { container } = renderIt();
    fireEvent.mouseEnter(screen.getByRole("link", { name: "Beta" }));
    const dimmed = circles(container).filter((c) => c.classList.contains("dim"));
    expect(dimmed).toHaveLength(1); // Gamma is not linked to Beta
  });

  it("hides the controls in the compact local graph and labels every node", () => {
    const { container } = renderIt({ current: "wikis/a.md" });
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(container.querySelectorAll("text")).toHaveLength(3);
  });
});
