import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// RTL auto-cleanup relies on vitest globals; we keep explicit imports, so clean up here.
afterEach(() => cleanup());
