/** CLI wiring: commander for args, injectable Io so tests can capture output. */
import { readFile } from "node:fs/promises";

import { Command } from "commander";
import { z } from "zod";

import { parseEvents } from "./schema.js";
import { formatTally, tally } from "./tally.js";

export interface Io {
  out: (line: string) => void;
  err: (line: string) => void;
}

const fieldSchema = z.enum(["event", "user"]); // CLI options are a boundary too

export async function run(
  argv: string[],
  io: Io = { out: console.log, err: console.error },
): Promise<number> {
  const program = new Command("tally")
    .description("Sum event counts in an NDJSON file, grouped by a field")
    .argument("<file>", "NDJSON file: one {event, user?, n?} object per line")
    .option("-f, --field <name>", "group by this field: event | user", "event")
    .exitOverride();

  try {
    program.parse(argv, { from: "user" });
  } catch {
    return 2; // commander already printed usage
  }

  const [file] = program.args;
  const fieldResult = fieldSchema.safeParse(program.opts<{ field: string }>().field);
  if (file === undefined || !fieldResult.success) {
    io.err("tally: --field must be one of: event, user");
    return 2;
  }

  try {
    const text = await readFile(file, "utf8");
    const rows = tally(parseEvents(text), fieldResult.data);
    io.out(formatTally(rows));
    return 0;
  } catch (error) {
    io.err(`tally: ${file}: ${error instanceof Error ? error.message : String(error)}`);
    return 1;
  }
}
