// STK-VITE-08: behavior, not implementation — accessible queries (getByRole,
// getByLabelText) and real user events; no assertions on hooks or internals.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import Home from "../src/routes/home";
import Settings from "../src/routes/settings";

// Fresh QueryClient per render: no cache bleed between tests, no retries in tests.
function renderWithQuery(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("Home", () => {
  it("shows the loading state, then the service list", async () => {
    renderWithQuery(<Home />);
    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
    const items = await screen.findAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "Backing API: up",
      "Database: up",
      "Job queue: down",
    ]);
  });
});

describe("Settings", () => {
  it("surfaces zod validation errors per field on empty submit", async () => {
    const user = userEvent.setup();
    renderWithQuery(<Settings />);

    await user.clear(screen.getByLabelText("Display name"));
    await user.clear(screen.getByLabelText("Email"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((a) => a.textContent)).toEqual([
      "Display name is required",
      "Enter a valid email",
    ]);
  });

  it("saves a valid profile and confirms", async () => {
    const user = userEvent.setup();
    renderWithQuery(<Settings />);

    await user.type(screen.getByLabelText("Display name"), "James F");
    await user.type(screen.getByLabelText("Email"), "james@example.com");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Saved.");
  });
});
