// The app's single server-state access module (STK-VITE-02): every query/mutation
// function lives here so components never hand-roll fetch. Replace the placeholder
// with real endpoints; components consume these only via useQuery/useMutation.
export type Ping = { ok: boolean; at: string };

export async function fetchPing(): Promise<Ping> {
  // Placeholder until a backing API exists (see examples/vite-react/ for the
  // fetch-swap pattern). Never move this logic into a component's useEffect.
  return { ok: true, at: new Date().toISOString() };
}
