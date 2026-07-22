/**
 * The boundary (STK-TS-06): raw NDJSON text crosses a zod schema here and flows
 * inward as inferred types. No `as` casts on external data anywhere else.
 */
import { z } from "zod";

export const eventSchema = z.object({
  event: z.string().min(1, "event name must be non-empty"),
  user: z.string().min(1).optional(),
  n: z.number().int().positive().default(1),
});

export type Event = z.infer<typeof eventSchema>;

/** Parse newline-delimited JSON events; errors carry 1-based line numbers. */
export function parseEvents(ndjson: string): Event[] {
  const events: Event[] = [];
  const lines = ndjson.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]?.trim();
    if (!line) continue; // blank lines (including trailing newline) are fine
    let raw: unknown;
    try {
      raw = JSON.parse(line);
    } catch {
      throw new Error(`line ${i + 1}: not valid JSON`);
    }
    const result = eventSchema.safeParse(raw);
    if (!result.success) {
      const issue = result.error.issues[0];
      const where = issue?.path.join(".") || "record";
      throw new Error(`line ${i + 1}: ${where}: ${issue?.message ?? "invalid"}`);
    }
    events.push(result.data);
  }
  return events;
}
