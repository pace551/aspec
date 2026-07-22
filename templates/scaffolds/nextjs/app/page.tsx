// Server component by default (STK-NEXT-02). Fetch data here, where it is used;
// add "use client" only on the interaction leaves this page renders. Mutations go
// through zod-validated server actions (STK-NEXT-03) — see examples/nextjs/.
export default function Home() {
  return (
    <main>
      <h1>{"{{PROJECT_NAME}}"}</h1>
    </main>
  );
}
