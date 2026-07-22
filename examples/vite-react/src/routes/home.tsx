// STK-VITE-02: server state via useQuery. STK-VITE-05: all three states rendered —
// pending, error (with retry), success. No fetch-in-useEffect anywhere.
import { useQuery } from "@tanstack/react-query";
import { fetchServices } from "../api";

export default function Home() {
  const { data, status, refetch } = useQuery({
    queryKey: ["services"],
    queryFn: fetchServices,
  });

  if (status === "pending") {
    return <p role="status">Loading services…</p>;
  }
  if (status === "error") {
    return (
      <div role="alert">
        <p>Could not load services.</p>
        <button onClick={() => refetch()}>Retry</button>
      </div>
    );
  }
  return (
    <section>
      <h2>Services</h2>
      <ul>
        {data.map((service) => (
          <li key={service.id}>
            {service.name}: <strong>{service.status}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}
