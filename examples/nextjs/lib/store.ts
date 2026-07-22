// In-memory store — real projects swap in SQLite/Postgres behind these functions
// without touching the action or the page. The globalThis anchor matters: Next.js
// keeps separate module graphs (RSC render vs server-action execution), so plain
// module state can exist twice — the same reason the Prisma-client-on-globalThis
// pattern exists. Anything smarter than this belongs in a real database.
export type Entry = { name: string; at: string };

const globalStore = globalThis as unknown as { __guestbookEntries?: Entry[] };
const entries: Entry[] = (globalStore.__guestbookEntries ??= []);

export function addEntry(name: string): Entry {
  const entry = { name, at: new Date().toISOString() };
  entries.push(entry);
  return entry;
}

export function listEntries(): Entry[] {
  return [...entries].reverse(); // newest first
}

export function resetEntries(): void {
  entries.length = 0; // test hook
}
