import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { snapshotFixture } from "../test/fixtures";
import { ItemDetails } from "./ItemDetails";

function setMobileViewport(matches: boolean): void {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: query === "(max-width: 767px)" && matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

function renderDetails(
  path: string,
  snapshot = snapshotFixture,
  initialEntries: string[] = [path],
) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route element={<p>Primary view</p>} path="/" />
        <Route
          element={<ItemDetails snapshot={snapshot} />}
          path="/items/:number"
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ItemDetails", () => {
  beforeEach(() => {
    setMobileViewport(false);
  });

  it("renders complete item details and sanitized issue HTML", () => {
    const snapshot = {
      ...snapshotFixture,
      items: [
        {
          ...snapshotFixture.items[0],
          bodyHtml:
            '<p>Safe issue content.</p><script data-testid="unsafe">alert(1)</script>',
        },
      ],
    };

    const { container } = renderDetails("/items/3", snapshot);

    expect(
      screen.getByRole("heading", {
        name: "Generate validated static Sonar content",
      }),
    ).toBeVisible();
    expect(screen.getByText("OPEN", { selector: "dd" })).toBeVisible();
    expect(screen.getByText("EXPLORE, PROPOSE")).toBeVisible();
    expect(screen.getByText("AI, WEB")).toBeVisible();
    expect(
      screen.getByText("September 15, 2026 at 6:00 PM UTC"),
    ).toBeVisible();
    expect(
      screen.getByText("Issue 3 requires an open pull request."),
    ).toBeVisible();
    expect(screen.getByText("Safe issue content.")).toBeVisible();
    expect(container.querySelector("script")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "PR #10: Approve the ADR (OPEN)" }),
    ).toHaveAttribute(
      "href",
      "https://github.com/sixfeetup/GH-Tech-Sonar/pull/10",
    );
    expect(
      screen.getByRole("link", { name: "View issue and history on GitHub" }),
    ).toHaveAttribute(
      "href",
      "https://github.com/sixfeetup/GH-Tech-Sonar/issues/3",
    );
  });

  it("renders an unknown-item message and a link to the primary view", () => {
    renderDetails("/items/999");

    expect(
      screen.getByRole("heading", { name: "Sonar item not found" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to Tech Sonar" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("offers mobile users history navigation and a direct home link", async () => {
    setMobileViewport(true);
    const user = userEvent.setup();
    renderDetails("/items/3", snapshotFixture, ["/", "/items/3"]);

    await user.click(screen.getByRole("button", { name: "Back" }));

    expect(screen.getByText("Primary view")).toBeVisible();
  });
});
