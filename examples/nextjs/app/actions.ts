"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { addEntry } from "../lib/store";

// STK-NEXT-03: a server action is a public endpoint — parse before use.
const Entry = z.object({
  name: z.string().trim().min(1).max(80),
});

export type SignState = { ok: boolean; error?: string };

export async function signGuestbook(
  _prev: SignState,
  formData: FormData,
): Promise<SignState> {
  const parsed = Entry.safeParse({ name: formData.get("name") });
  if (!parsed.success) {
    // Typed field error for the form's error state (UX-FORMS).
    return { ok: false, error: "Name must be 1-80 characters." };
  }
  addEntry(parsed.data.name);
  revalidatePath("/");
  return { ok: true };
}
