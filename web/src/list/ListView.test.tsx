import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SonarItem } from "../data/sonar";
import { snapshotFixture } from "../test/fixtures";
import { ListView } from "./ListView";

const detailedItem = snapshotFixture.items[0];
const newestItem: SonarItem = {
  ...detailedItem,
  number: 8,
  title: "A newer Sonar item",
  statuses: ["ADOPT"],
  categories: ["WEB"],
  pullRequests: [],
  warnings: [],
};

describe("ListView", () => {
  it("sorts item links by descending issue number", () => {
    render(<ListView items={[detailedItem, newestItem]} />);

    const itemLinks = screen.getAllByRole("link", { name: /Sonar item|static/ });
    expect(itemLinks.map((link) => link.textContent)).toEqual([
      "#8 A newer Sonar item",
      "#3 Generate validated static Sonar content",
    ]);
    expect(itemLinks[0]).toHaveAttribute("href", "/#/items/8");
  });

  it("renders one row per item with all list information", () => {
    render(<ListView items={[detailedItem]} />);

    expect(
      screen.getAllByRole("link", {
        name: "#3 Generate validated static Sonar content",
      }),
    ).toHaveLength(1);

    const row = screen.getByRole("article");
    expect(within(row).getByText("EXPLORE, PROPOSE")).toBeVisible();
    expect(within(row).getByText("AI, WEB")).toBeVisible();
    expect(within(row).getByText("2026-09-15")).toBeVisible();
    expect(
      within(row).getByText("Issue 3 requires an open pull request."),
    ).toBeVisible();
    expect(
      within(row).getByRole("link", { name: "PR #10: Approve the ADR (OPEN)" }),
    ).toHaveAttribute(
      "href",
      "https://github.com/sixfeetup/GH-Tech-Sonar/pull/10",
    );
  });

  it("renders an empty result message", () => {
    render(<ListView items={[]} />);

    expect(
      screen.getByText("No Sonar items match these filters."),
    ).toBeVisible();
  });
});
