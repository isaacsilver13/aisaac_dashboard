import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { readToken } from "../token";
import Settings from "./Settings";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("Settings", () => {
  it("saves and clears the dashboard token", async () => {
    render(<Settings />);
    await userEvent.type(screen.getByLabelText("Dashboard token"), " abc ");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(readToken()).toBe("abc");
    expect(screen.getByText("A token is saved.")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(readToken()).toBe("");
  });
});
