import { describe, expect, it } from "vitest";

import type { SonarItem } from "../data/sonar";
import { snapshotFixture as baseFixture } from "../test/fixtures";
import {
  categoriesFor,
  defaultFilters,
  filterItems,
} from "./filtering";

const item = baseFixture.items[0];
const items: SonarItem[] = [
  item,
  {
    ...item,
    number: 4,
    updatedAt: "2026-09-17T00:00:00Z",
    statuses: ["HOLD"],
    categories: ["AI"],
  },
  {
    ...item,
    number: 5,
    updatedAt: "2026-09-16T23:59:59Z",
    statuses: ["HOLD"],
    categories: ["AI"],
  },
];
const snapshotFixture = { ...baseFixture, items };
const allFilters = {
  category: "ALL",
  updatedSince: "",
  status: "ALL",
} as const;

describe("filterItems", () => {
  it("filters by category, status, and inclusive update date", () => {
    const result = filterItems(snapshotFixture.items, {
      category: "AI",
      updatedSince: "2026-09-17",
      status: "HOLD",
    });

    expect(result.map((filteredItem) => filteredItem.number)).toEqual([4]);
  });

  it("returns every item for default filters", () => {
    expect(filterItems(snapshotFixture.items, allFilters)).toEqual(
      snapshotFixture.items,
    );
  });
});

describe("filter options", () => {
  it("provides sorted unique categories", () => {
    expect(categoriesFor(snapshotFixture.items)).toEqual(["AI", "WEB"]);
  });

  it("exports the default filters", () => {
    expect(defaultFilters).toEqual(allFilters);
  });
});
