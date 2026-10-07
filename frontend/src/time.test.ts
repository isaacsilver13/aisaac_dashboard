import { describe, expect, it } from "vitest";

import { centralTimestamp, exactTimestamp, humanizeTimestamp } from "./time";

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

  it("formats precise dashboard metadata in Central time", () => {
    expect(centralTimestamp("2026-01-01T18:30:00Z")).toBe("Jan 1, 2026 12:30:00PM CST");
    expect(centralTimestamp("2026-07-01T17:30:00Z")).toBe("Jul 1, 2026 12:30:00PM CDT");
  });
});
