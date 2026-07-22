/** Pure tally logic: no I/O here. */
import type { Event } from "./schema.js";

export type TallyField = "event" | "user";

export interface TallyRow {
  key: string;
  total: number;
}

/**
 * Sum `n` grouped by the chosen field, sorted by total desc then key asc.
 * Records missing an optional field (e.g. `user`) are skipped.
 */
export function tally(events: Event[], field: TallyField): TallyRow[] {
  const totals = new Map<string, number>();
  for (const ev of events) {
    const key = field === "event" ? ev.event : ev.user;
    if (key === undefined) continue;
    totals.set(key, (totals.get(key) ?? 0) + ev.n);
  }
  return [...totals.entries()]
    .map(([key, total]) => ({ key, total }))
    .sort((a, b) => b.total - a.total || a.key.localeCompare(b.key));
}

export function formatTally(rows: TallyRow[]): string {
  const width = Math.max(0, ...rows.map((r) => r.key.length));
  return rows.map((r) => `${r.key.padEnd(width)}  ${r.total}`).join("\n");
}
