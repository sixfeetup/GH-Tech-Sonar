import { useCallback, useEffect, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";

import { SiteLayout } from "./branding/SiteChrome";
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
  const contributionRef = useRef<HTMLDialogElement>(null);
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

  useEffect(() => {
    if (!showContribution) {
      return;
    }

    const closeOnOutsidePointer = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        !contributionRef.current?.contains(target) &&
        !contributeButtonRef.current?.contains(target)
      ) {
        setShowContribution(false);
      }
    };

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
    };
  }, [showContribution]);

  const closeContribution = () => {
    setShowContribution(false);
    contributeButtonRef.current?.focus();
  };

  if (state.status === "loading") {
    return (
      <SiteLayout>
        <div className="status-message" role="status">
          <div aria-hidden="true" className="spinner" />
          <p>Loading Tech Sonar…</p>
        </div>
      </SiteLayout>
    );
  }

  if (state.status === "error") {
    return (
      <SiteLayout>
        <div className="status-message">
          <p>Unable to load Tech Sonar: {state.message}</p>
          <button className="error-retry" type="button" onClick={load}>
            Retry
          </button>
        </div>
      </SiteLayout>
    );
  }

  const filteredItems = filterItems(state.snapshot.items, filters);
  const newTechnologyUrl =
    `https://github.com/${state.snapshot.repository}/issues/new` +
    "?template=technology.yml";
  const contribution = showContribution ? (
    <dialog
      aria-labelledby="contribute-heading"
      className="contribution-popover"
      id="contribution-popover"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          closeContribution();
        }
      }}
      open
      ref={contributionRef}
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
  ) : undefined;
  const contributeControl = (
    <div className="contribution-control">
      <button
        aria-controls="contribution-popover"
        aria-expanded={showContribution}
        className="contribute-toggle"
        onClick={() => setShowContribution(true)}
        ref={contributeButtonRef}
        type="button"
      >
        Contribute!
      </button>
      {contribution}
    </div>
  );

  return (
    <SiteLayout actions={contributeControl}>
      <Routes>
        <Route
          path="/"
          element={
            <>
              <h1 className="visually-hidden">Tech Sonar</h1>
              <Filters
                categories={categoriesFor(state.snapshot.items)}
                filters={filters}
                onFiltersChange={setFilters}
                onViewChange={setView}
                view={view}
              />
              {view === "list" ? (
                <ListView
                  items={filteredItems}
                  totalCount={state.snapshot.items.length}
                />
              ) : (
                <SonarView
                  items={filteredItems}
                  totalCount={state.snapshot.items.length}
                />
              )}
            </>
          }
        />
        <Route
          path="/items/:number"
          element={<ItemDetails snapshot={state.snapshot} />}
        />
      </Routes>
    </SiteLayout>
  );
}
