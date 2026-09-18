import type { SonarItem, Status } from "../data/sonar";

export type ViewMode = "sonar" | "list";
export type CategoryFilter = "ALL" | string;
export type StatusFilter = "ALL" | Status;

export interface FilterState {
  category: CategoryFilter;
  updatedSince: string;
  status: StatusFilter;
}

export const defaultFilters: FilterState = {
  category: "ALL",
  updatedSince: "",
  status: "ALL",
};

export function filterItems(
  items: SonarItem[],
  filters: FilterState,
): SonarItem[] {
  const updatedSince = filters.updatedSince
    ? new Date(`${filters.updatedSince}T00:00:00.000Z`).getTime()
    : undefined;

  return items.filter(
    (item) =>
      (filters.category === "ALL" ||
        item.categories.includes(filters.category)) &&
      (filters.status === "ALL" || item.statuses.includes(filters.status)) &&
      (updatedSince === undefined ||
        new Date(item.updatedAt).getTime() >= updatedSince),
  );
}

export function categoriesFor(items: SonarItem[]): string[] {
  return [...new Set(items.flatMap((item) => item.categories))].sort((a, b) =>
    a.localeCompare(b),
  );
}
