import { describe, expect, test } from "vitest";

import type { Event } from "../src/schema.js";
import { formatTally, tally } from "../src/tally.js";

const EVENTS: Event[] = [
  { event: "login", user: "alice", n: 1 },
  { event: "click", user: "bob", n: 3 },
  { event: "login", user: "bob", n: 1 },
  { event: "export", n: 2 }, // no user — skipped when grouping by user
];

describe("tally", () => {
  test("sums n by event, sorted by total desc then key asc", () => {
    expect(tally(EVENTS, "event")).toEqual([
      { key: "click", total: 3 },
      { key: "export", total: 2 },
      { key: "login", total: 2 },
    ]);
  });

  test("grouping by an optional field skips records without it", () => {
    expect(tally(EVENTS, "user")).toEqual([
      { key: "bob", total: 4 },
      { key: "alice", total: 1 },
    ]);
  });

  test("empty input tallies to an empty table", () => {
    expect(tally([], "event")).toEqual([]);
    expect(formatTally([])).toBe("");
  });

  test("formatTally aligns keys into columns", () => {
    expect(formatTally(tally(EVENTS, "event"))).toBe("click   3\nexport  2\nlogin   2");
  });
});
