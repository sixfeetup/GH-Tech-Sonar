import { useCallback, useEffect, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";

import { loadSnapshot, type SonarSnapshot } from "./data/sonar";
import { ItemDetails } from "./details/ItemDetails";
import { Filters } from "./filters/Filters";
import {
  categoriesFor,
  defaultFilters,
  filterItems,
  type FilterState,
  type ViewMode,
} from "./filters/filtering";
import { ListView } from "./list/ListView";
import { SonarView } from "./sonar/SonarView";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; snapshot: SonarSnapshot };

export function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [showContribution, setShowContribution] = useState(false);
  const contributeButtonRef = useRef<HTMLButtonElement>(null);
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

  const closeContribution = () => {
    setShowContribution(false);
    contributeButtonRef.current?.focus();
  };

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
  const newTechnologyUrl =
    `https://github.com/${state.snapshot.repository}/issues/new` +
    "?template=technology.yml";

  return (
    <main>
      <Routes>
        <Route
          path="/"
          element={
            <>
              <h1>
                {state.snapshot.repository}: {state.snapshot.items.length} items
              </h1>
              <Filters
                categories={categoriesFor(state.snapshot.items)}
                filters={filters}
                onContribute={(trigger) => {
                  contributeButtonRef.current = trigger;
                  setShowContribution(true);
                }}
                onFiltersChange={setFilters}
                onViewChange={setView}
                view={view}
              />
              {view === "list" ? (
                <ListView items={filteredItems} />
              ) : (
                <SonarView items={filteredItems} />
              )}
            </>
          }
        />
        <Route
          path="/items/:number"
          element={<ItemDetails snapshot={state.snapshot} />}
        />
      </Routes>
      {showContribution && (
        <dialog
          aria-labelledby="contribute-heading"
          aria-modal="true"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              closeContribution();
            }
          }}
          open
        >
          <h2 id="contribute-heading">Contribute</h2>
          <p>
            You can add a technology by opening a{" "}
            <a href={newTechnologyUrl} rel="noreferrer" target="_blank">
              Technology issue
            </a>{" "}
            in the source repository.
          </p>
          <p>
            See the{" "}
            <a
              href="https://github.com/sixfeetup/GH-Tech-Sonar/blob/main/docs/using-tech-sonar.md"
              rel="noreferrer"
              target="_blank"
            >
              Tech Sonar documentation
            </a>.
          </p>
          <button autoFocus type="button" onClick={closeContribution}>
            Close
          </button>
        </dialog>
      )}
    </main>
  );
}
