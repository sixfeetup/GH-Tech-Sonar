import { useCallback, useEffect, useState } from "react";

import { loadSnapshot, type SonarSnapshot } from "./data/sonar";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; snapshot: SonarSnapshot };

export function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const snapshot = await loadSnapshot();
      setState({ status: "loaded", snapshot });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status === "loading") {
    return <main>Loading Tech Sonar…</main>;
  }

  if (state.status === "error") {
    return (
      <main>
        <p>Unable to load Tech Sonar: {state.message}</p>
        <button type="button" onClick={load}>
          Retry
        </button>
      </main>
    );
  }

  return (
    <main>
      <h1>
        {state.snapshot.repository}: {state.snapshot.items.length} items
      </h1>
    </main>
  );
}
