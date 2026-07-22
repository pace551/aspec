"use client";

// STK-NEXT-02: the ONLY client component — the interaction leaf. The page and layout
// stay server components; this island owns pending/error state and nothing else.
import { useActionState } from "react";
import { signGuestbook, type SignState } from "./actions";

const initialState: SignState = { ok: false };

export function GuestForm() {
  const [state, formAction, pending] = useActionState(
    signGuestbook,
    initialState,
  );

  return (
    <form action={formAction}>
      <label htmlFor="name">Name</label>{" "}
      <input id="name" name="name" required maxLength={80} />{" "}
      <button type="submit" disabled={pending}>
        {pending ? "Signing…" : "Sign"}
      </button>
      {state.error ? <p role="alert">{state.error}</p> : null}
    </form>
  );
}
