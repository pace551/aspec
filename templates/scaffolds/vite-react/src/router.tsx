// STK-VITE-03: react-router data router; routes are the unit of structure.
// STK-VITE-05: errorElement at route level. STK-VITE-06: routes code-split via lazy.
import { lazy, Suspense } from "react";
import { createBrowserRouter, Link, Outlet, useRouteError } from "react-router";

const Home = lazy(() => import("./routes/home"));

function Layout() {
  return (
    <main>
      <h1>{"{{PROJECT_NAME}}"}</h1>
      <Suspense fallback={<p role="status">Loading…</p>}>
        <Outlet />
      </Suspense>
    </main>
  );
}

export function RouteError() {
  const error = useRouteError();
  return (
    <div role="alert">
      <h2>Something broke in this pane.</h2>
      <p>{error instanceof Error ? error.message : "Unknown error"}</p>
      <Link to="/">Back to home</Link>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <RouteError />,
    children: [{ index: true, element: <Home /> }],
  },
]);
