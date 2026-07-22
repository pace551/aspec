import { describe, expect, test } from "vitest";

import { parseEvents } from "../src/schema.js";

describe("parseEvents (the zod boundary)", () => {
  test("parses valid lines and applies the n default", () => {
    const events = parseEvents('{"event":"login","user":"alice"}\n{"event":"click","n":3}\n');
    expect(events).toEqual([
      { event: "login", user: "alice", n: 1 },
      { event: "click", n: 3 },
    ]);
  });

  test("blank lines are ignored", () => {
    expect(parseEvents('\n{"event":"a"}\n\n')).toHaveLength(1);
  });

  test("invalid JSON reports the 1-based line number", () => {
    expect(() => parseEvents('{"event":"ok"}\n{oops')).toThrow("line 2: not valid JSON");
  });

  test("schema violations report line and field", () => {
    expect(() => parseEvents('{"event":""}')).toThrow(/line 1: event/);
    expect(() => parseEvents('{"event":"x","n":-2}')).toThrow(/line 1: n/);
  });
});
