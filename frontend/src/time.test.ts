import { describe, expect, it } from "vitest";

import { exactTimestamp, humanizeTimestamp } from "./time";

const NOW = new Date(2026, 9, 6, 14, 0, 0);

describe("humanizeTimestamp", () => {
  it("uses relative labels for recent activity", () => {
    expect(humanizeTimestamp(new Date(2026, 9, 6, 13, 55).toISOString(), NOW)).toBe("5 minutes ago");
    expect(humanizeTimestamp(new Date(2026, 9, 6, 13, 0).toISOString(), NOW)).toBe("1 hour ago");
  });

  it("uses a day-aware label for older data freshness", () => {
    expect(humanizeTimestamp(new Date(2026, 9, 5, 9, 30).toISOString(), NOW)).toMatch(/^Yesterday at /);
  });

  it("keeps invalid timestamps explicit", () => {
    expect(humanizeTimestamp("not-a-date", NOW)).toBe("Unknown time");
    expect(exactTimestamp("not-a-date")).toBe("not-a-date");
  });
});
