// The app's single server-state access module (STK-VITE-02): every query/mutation
// function lives here. Fake latency stands in for a real backing API — swap the
// bodies for fetch() calls without touching components.
export type Service = { id: string; name: string; status: "up" | "down" };
export type Profile = { displayName: string; email: string };

const services: Service[] = [
  { id: "api", name: "Backing API", status: "up" },
  { id: "db", name: "Database", status: "up" },
  { id: "queue", name: "Job queue", status: "down" },
];

let profile: Profile = { displayName: "James", email: "james@example.com" };

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function fetchServices(): Promise<Service[]> {
  await sleep(10);
  return services.map((s) => ({ ...s }));
}

export async function fetchProfile(): Promise<Profile> {
  await sleep(10);
  return { ...profile };
}

export async function saveProfile(next: Profile): Promise<Profile> {
  await sleep(10);
  profile = { ...next };
  return { ...profile };
}
