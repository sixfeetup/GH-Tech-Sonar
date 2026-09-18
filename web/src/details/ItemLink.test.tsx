import { render, screen } from "@testing-library/react";
import { HashRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ItemLink } from "./ItemLink";

function setViewportWidth(width: number): void {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: query === "(max-width: 767px)" && width <= 767,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

describe("ItemLink", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("opens an item in a new tab at desktop width", () => {
    setViewportWidth(1024);

    render(
      <HashRouter>
        <ItemLink aria-label="Read item 3" number={3}>
          Item 3
        </ItemLink>
      </HashRouter>,
    );

    const link = screen.getByRole("link", { name: "Read item 3" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveProperty("href", "http://localhost:3000/#/items/3");
  });

  it("opens an item in the current tab at mobile width", () => {
    setViewportWidth(390);

    render(
      <HashRouter>
        <ItemLink aria-label="Open item 3" number={3}>
          Item 3
        </ItemLink>
      </HashRouter>,
    );

    const link = screen.getByRole("link", { name: "Open item 3" });
    expect(link).not.toHaveAttribute("target");
    expect(link).not.toHaveAttribute("rel");
    expect(link).toHaveProperty("href", "http://localhost:3000/#/items/3");
  });
});
