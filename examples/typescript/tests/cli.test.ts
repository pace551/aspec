import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { beforeEach, describe, expect, test } from "vitest";

import type { Io } from "../src/cli.js";
import { run } from "../src/cli.js";

const NDJSON = '{"event":"login","user":"alice"}\n{"event":"login","n":4}\n';

let out: string[];
let err: string[];
let io: Io;

beforeEach(() => {
  out = [];
  err = [];
  io = { out: (l) => out.push(l), err: (l) => err.push(l) };
});

async function tmpFile(contents: string): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), "tally-"));
  const file = join(dir, "events.ndjson");
  await writeFile(file, contents);
  return file;
}

describe("run (end to end)", () => {
  test("tallies a real file and prints the table", async () => {
    const file = await tmpFile(NDJSON);
    expect(await run([file], io)).toBe(0);
    expect(out.join("\n")).toBe("login  5");
  });

  test("missing file exits 1 with a diagnostic on stderr", async () => {
    expect(await run(["/nonexistent/events.ndjson"], io)).toBe(1);
    expect(err[0]).toMatch(/^tally: \/nonexistent\/events\.ndjson: /);
  });

  test("bad --field exits 2 with usage guidance", async () => {
    const file = await tmpFile(NDJSON);
    expect(await run([file, "--field", "color"], io)).toBe(2);
    expect(err[0]).toContain("--field must be one of");
  });

  test("malformed line surfaces the boundary error", async () => {
    const file = await tmpFile('{"event":""}\n');
    expect(await run([file], io)).toBe(1);
    expect(err[0]).toContain("line 1: event");
  });
});
