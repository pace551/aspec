// Server component by default (STK-NEXT-02): reads data where it lives, no client
// fetch. The interactive form is the single "use client" leaf it renders.
import type { Metadata } from "next";
import { listEntries } from "../lib/store";
import { GuestForm } from "./guest-form";

export const metadata: Metadata = { title: "Sign the book" };
export const dynamic = "force-dynamic"; // entries change per request

export default function Home() {
  const entries = listEntries();
  return (
    <main>
      <h1>Guestbook</h1>
      <GuestForm />
      <h2>Signatures</h2>
      {entries.length === 0 ? (
        <p>No signatures yet.</p>
      ) : (
        <ul>
          {entries.map((entry) => (
            <li key={`${entry.at}-${entry.name}`}>{entry.name}</li>
          ))}
        </ul>
      )}
    </main>
  );
}
