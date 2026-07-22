// STK-VITE-02: server state via useQuery. STK-VITE-05: all three states rendered.
import { useQuery } from "@tanstack/react-query";
import { fetchPing } from "../api";

export default function Home() {
  const { data, status, refetch } = useQuery({
    queryKey: ["ping"],
    queryFn: fetchPing,
  });

  if (status === "pending") {
    return <p role="status">Loading…</p>;
  }
  if (status === "error") {
    return (
      <div role="alert">
        <p>Could not load.</p>
        <button onClick={() => refetch()}>Retry</button>
      </div>
    );
  }
  return <p>Ready since {data.at}.</p>;
}
