import { useCallback, useEffect, useState } from "react";

import { loadSnapshot, type SonarSnapshot } from "./data/sonar";
import { Filters } from "./filters/Filters";
import {
  categoriesFor,
  defaultFilters,
  filterItems,
  type FilterState,
  type ViewMode,
} from "./filters/filtering";
import { ListView } from "./list/ListView";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; snapshot: SonarSnapshot };

export function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [view, setView] = useState<ViewMode>("sonar");
  const [filters, setFilters] = useState<FilterState>(defaultFilters);

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

  const filteredItems = filterItems(state.snapshot.items, filters);

  return (
    <main>
      <h1>
        {state.snapshot.repository}: {state.snapshot.items.length} items
      </h1>
      <Filters
        categories={categoriesFor(state.snapshot.items)}
        filters={filters}
        onFiltersChange={setFilters}
        onViewChange={setView}
        view={view}
      />
      {view === "list" ? (
        <ListView items={filteredItems} />
      ) : (
        <section className="sonar-placeholder">
          <h2>Sonar</h2>
          <p>Sonar visualization coming soon.</p>
        </section>
      )}
    </main>
  );
}
