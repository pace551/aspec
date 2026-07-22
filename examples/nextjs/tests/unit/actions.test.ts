// STK-NEXT-08: server actions unit-tested as plain async functions — zod rejection
// paths first, then the happy path. next/cache is mocked; no server needed.
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import { signGuestbook } from "../../app/actions";
import { listEntries, resetEntries } from "../../lib/store";

function form(name: string | null): FormData {
  const fd = new FormData();
  if (name !== null) fd.set("name", name);
  return fd;
}

const prev = { ok: false };

describe("signGuestbook", () => {
  beforeEach(() => resetEntries());

  it("rejects a missing name", async () => {
    const result = await signGuestbook(prev, form(null));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/1-80/);
    expect(listEntries()).toHaveLength(0);
  });

  it("rejects a whitespace-only name", async () => {
    const result = await signGuestbook(prev, form("   "));
    expect(result.ok).toBe(false);
    expect(listEntries()).toHaveLength(0);
  });

  it("rejects a name over 80 characters", async () => {
    const result = await signGuestbook(prev, form("x".repeat(81)));
    expect(result.ok).toBe(false);
    expect(listEntries()).toHaveLength(0);
  });

  it("stores a trimmed valid name", async () => {
    const result = await signGuestbook(prev, form("  Ada Lovelace  "));
    expect(result).toEqual({ ok: true });
    expect(listEntries().map((e) => e.name)).toEqual(["Ada Lovelace"]);
  });
});
