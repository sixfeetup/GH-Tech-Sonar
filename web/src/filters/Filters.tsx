import type { Status } from "../data/sonar";
import type {
  CategoryFilter,
  FilterState,
  StatusFilter,
  ViewMode,
} from "./filtering";

const statuses: Status[] = [
  "ADOPT",
  "PROPOSE",
  "EXPLORE",
  "HOLD",
  "REJECT",
];

interface FiltersProps {
  categories: string[];
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onViewChange: (view: ViewMode) => void;
  view: ViewMode;
}

export function Filters({
  categories,
  filters,
  onFiltersChange,
  onViewChange,
  view,
}: FiltersProps) {
  return (
    <section aria-label="Sonar controls" className="controls">
      <div aria-label="View" className="view-toggle" role="group">
        <button
          aria-pressed={view === "sonar"}
          onClick={() => onViewChange("sonar")}
          type="button"
        >
          Sonar
        </button>
        <button
          aria-pressed={view === "list"}
          onClick={() => onViewChange("list")}
          type="button"
        >
          List
        </button>
      </div>

      <label>
        Category
        <select
          onChange={(event) =>
            onFiltersChange({
              ...filters,
              category: event.target.value as CategoryFilter,
            })
          }
          value={filters.category}
        >
          <option value="ALL">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </label>

      <label>
        Updated since
        <input
          onChange={(event) =>
            onFiltersChange({
              ...filters,
              updatedSince: event.target.value,
            })
          }
          type="date"
          value={filters.updatedSince}
        />
      </label>

      <label>
        Status
        <select
          onChange={(event) =>
            onFiltersChange({
              ...filters,
              status: event.target.value as StatusFilter,
            })
          }
          value={filters.status}
        >
          <option value="ALL">All statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}
