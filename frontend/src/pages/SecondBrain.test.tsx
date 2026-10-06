import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Note } from "../types";

const api = vi.hoisted(() => ({ fetchNote: vi.fn() }));
vi.mock("../api", async (orig) => ({
  ...(await orig<typeof import("../api")>()),
  fetchNotes: vi.fn().mockResolvedValue([]),
  fetchPortals: vi.fn().mockResolvedValue([]),
  fetchGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  fetchNote: api.fetchNote,
}));

import SecondBrain from "./SecondBrain";

const note = (path: string, title: string): Note => ({
  path,
  folder: "wikis",
  title,
  aliases: [],
  status: null,
  body: "",
  frontmatter: {},
  link_map: {},
  links: [],
  backlinks: [],
  previews: {},
  portal: "wikis/apps",
});

function GoToB() {
  const navigate = useNavigate();
  return <button onClick={() => navigate("/knowledge/wikis/apps/b")}>go b</button>;
}

beforeEach(() => localStorage.setItem("aisaac.dashboardToken", "t"));
afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("SecondBrain article route", () => {
  it("shows the newest article even when an older request resolves last", async () => {
    let resolveA!: (n: Note) => void;
    api.fetchNote.mockImplementation((_token: string, path: string) =>
      path.endsWith("/a.md") ? new Promise<Note>((r) => (resolveA = r)) : Promise.resolve(note(path, "Article B")),
    );
    render(
      <MemoryRouter initialEntries={["/knowledge/wikis/apps/a"]}>
        <GoToB />
        <Routes>
          <Route path="/knowledge/*" element={<SecondBrain />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(api.fetchNote).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByText("go b"));
    expect(await screen.findByRole("heading", { level: 1, name: "Article B" })).toBeInTheDocument();
    resolveA(note("wikis/apps/a.md", "Article A"));
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByRole("heading", { level: 1, name: "Article B" })).toBeInTheDocument();
  });
});
