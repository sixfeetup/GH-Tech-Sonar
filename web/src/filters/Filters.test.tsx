import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Filters } from "./Filters";
import {
  defaultFilters,
  type FilterState,
  type ViewMode,
} from "./filtering";

function ControlledFilters({
  onFiltersChange,
  onViewChange,
}: {
  onFiltersChange: (filters: FilterState) => void;
  onViewChange: (view: ViewMode) => void;
}) {
  const [filters, setFilters] = useState(defaultFilters);
  const [view, setView] = useState<ViewMode>("sonar");

  return (
    <Filters
      categories={["AI", "WEB"]}
      filters={filters}
      onContribute={vi.fn()}
      onFiltersChange={(nextFilters) => {
        onFiltersChange(nextFilters);
        setFilters(nextFilters);
      }}
      onViewChange={(nextView) => {
        onViewChange(nextView);
        setView(nextView);
      }}
      view={view}
    />
  );
}

describe("Filters", () => {
  it("orders view, category, update date, and status controls", () => {
    const { container } = render(
      <Filters
        categories={["AI", "WEB"]}
        filters={defaultFilters}
        onContribute={vi.fn()}
        onFiltersChange={vi.fn()}
        onViewChange={vi.fn()}
        view="sonar"
      />,
    );

    expect([...container.querySelectorAll("button, select, input")]).toEqual([
      screen.getByRole("button", { name: "Sonar" }),
      screen.getByRole("button", { name: "List" }),
      screen.getByRole("combobox", { name: "Category" }),
      screen.getByLabelText("Updated since"),
      screen.getByRole("combobox", { name: "Status" }),
      screen.getByRole("button", { name: "Contribute" }),
    ]);
  });

  it("reports controlled view and filter changes", async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const onViewChange = vi.fn();
    render(
      <ControlledFilters
        onFiltersChange={onFiltersChange}
        onViewChange={onViewChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "List" }));
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Category" }),
      "AI",
    );
    await user.type(screen.getByLabelText("Updated since"), "2026-09-17");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Status" }),
      "HOLD",
    );

    expect(onViewChange).toHaveBeenCalledWith("list");
    expect(onFiltersChange).toHaveBeenNthCalledWith(1, {
      ...defaultFilters,
      category: "AI",
    });
    expect(onFiltersChange).toHaveBeenNthCalledWith(2, {
      category: "AI",
      updatedSince: "2026-09-17",
      status: "ALL",
    });
    expect(onFiltersChange).toHaveBeenNthCalledWith(3, {
      category: "AI",
      updatedSince: "2026-09-17",
      status: "HOLD",
    });
  });

  it("shows the default filter values", () => {
    render(
      <Filters
        categories={["AI", "WEB"]}
        filters={defaultFilters}
        onContribute={vi.fn()}
        onFiltersChange={vi.fn()}
        onViewChange={vi.fn()}
        view="sonar"
      />,
    );

    expect(screen.getByRole("combobox", { name: "Category" })).toHaveValue(
      "ALL",
    );
    expect(screen.getByRole("option", { name: "All categories" })).toBeVisible();
    expect(screen.getByLabelText("Updated since")).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Status" })).toHaveValue(
      "ALL",
    );
    expect(screen.getByRole("option", { name: "All statuses" })).toBeVisible();
  });
});
